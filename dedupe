#!/usr/bin/env python3
"""
File Deduplication Tool - Like mini rsync
A high-performance file deduplication utility with incremental scanning.

Usage:
    dedupe scan ./folder              # Scan for duplicates
    dedupe clean --dry-run            # Preview what would be deleted
    dedupe clean                      # Actually remove duplicates
"""

import os
import sys
import json
import hashlib
import sqlite3
import argparse
import threading
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from functools import partial
from typing import Dict, List, Set, Tuple, Optional, Iterator
from dataclasses import dataclass, asdict

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich.panel import Panel
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ============================================================================
# Configuration & Constants
# ============================================================================

CHUNK_SIZE = 8192  # 8KB chunks for reading
LARGE_FILE_THRESHOLD = 100 * 1024 * 1024  # 100MB
SMALL_HASH_SIZE = 4096  # First 4KB for quick comparison
STATE_DB_NAME = ".dedupe_state.db"

console = Console() if RICH_AVAILABLE else None

# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FileInfo:
    """Represents a file with its metadata and hashes."""
    path: str
    size: int
    mtime: float
    quick_hash: str  # Hash of first 4KB
    full_hash: Optional[str] = None  # Full file hash (computed on demand)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'FileInfo':
        return cls(**data)

@dataclass
class DuplicateGroup:
    """A group of duplicate files."""
    size: int
    hash: str
    files: List[str]
    
    @property
    def wasted_space(self) -> int:
        return self.size * (len(self.files) - 1)

# ============================================================================
# State Database (Incremental Scanning)
# ============================================================================

class StateDatabase:
    """SQLite-backed state for incremental scanning."""
    
    def __init__(self, db_path: str = STATE_DB_NAME):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime REAL NOT NULL,
                quick_hash TEXT NOT NULL,
                full_hash TEXT,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_size ON files(size);
            CREATE INDEX IF NOT EXISTS idx_hash ON files(quick_hash);
            CREATE INDEX IF NOT EXISTS idx_full_hash ON files(full_hash);
            
            CREATE TABLE IF NOT EXISTS scan_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        ''')
        conn.commit()
        conn.close()
    
    def get_cached(self, path: str, mtime: float, size: int) -> Optional[FileInfo]:
        """Get cached file info if still valid."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM files WHERE path = ? AND mtime = ? AND size = ?",
            (path, mtime, size)
        ).fetchone()
        
        if row:
            return FileInfo(
                path=row['path'],
                size=row['size'],
                mtime=row['mtime'],
                quick_hash=row['quick_hash'],
                full_hash=row['full_hash']
            )
        return None
    
    def update(self, file_info: FileInfo):
        """Update or insert file info."""
        conn = self._get_conn()
        conn.execute('''
            INSERT OR REPLACE INTO files (path, size, mtime, quick_hash, full_hash, scanned_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (file_info.path, file_info.size, file_info.mtime, 
              file_info.quick_hash, file_info.full_hash))
        conn.commit()
    
    def update_full_hash(self, path: str, full_hash: str):
        """Update full hash for a file."""
        conn = self._get_conn()
        conn.execute(
            "UPDATE files SET full_hash = ? WHERE path = ?",
            (full_hash, path)
        )
        conn.commit()
    
    def remove_missing(self, existing_paths: Set[str]) -> int:
        """Remove entries for files that no longer exist."""
        conn = self._get_conn()
        cursor = conn.execute("SELECT path FROM files")
        to_remove = [row['path'] for row in cursor if row['path'] not in existing_paths]
        
        for path in to_remove:
            conn.execute("DELETE FROM files WHERE path = ?", (path,))
        
        conn.commit()
        return len(to_remove)
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        with_full = conn.execute(
            "SELECT COUNT(*) FROM files WHERE full_hash IS NOT NULL"
        ).fetchone()[0]
        return {"total": total, "with_full_hash": with_full}

# ============================================================================
# Hashing Engine
# ============================================================================

class HashEngine:
    """Fast and efficient file hashing with chunk-based comparison."""
    
    @staticmethod
    def quick_hash(filepath: str) -> str:
        """Hash first 4KB of file for fast comparison."""
        hasher = hashlib.blake2b(digest_size=16)
        try:
            with open(filepath, 'rb') as f:
                hasher.update(f.read(SMALL_HASH_SIZE))
            return hasher.hexdigest()
        except (IOError, OSError):
            return ""
    
    @staticmethod
    def full_hash(filepath: str, progress_callback=None) -> str:
        """Compute full file hash with progress updates."""
        hasher = hashlib.blake2b(digest_size=32)
        try:
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    if progress_callback:
                        progress_callback(len(chunk))
            return hasher.hexdigest()
        except (IOError, OSError):
            return ""
    
    @staticmethod
    def chunked_compare(file1: str, file2: str, chunk_size: int = CHUNK_SIZE) -> bool:
        """Compare two files chunk by chunk without loading entirely into memory."""
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                while True:
                    c1 = f1.read(chunk_size)
                    c2 = f2.read(chunk_size)
                    if c1 != c2:
                        return False
                    if not c1:  # EOF
                        return True
        except (IOError, OSError):
            return False

# ============================================================================
# File System Traversal
# ============================================================================

class FileTraverser:
    """Efficient filesystem traversal with filtering."""
    
    DEFAULT_EXCLUDES = {
        '.git', '.svn', '.hg',  # Version control
        'node_modules', '__pycache__', '.pytest_cache',
        '.venv', 'venv', '.env',
        '.dedupe_state.db',  # Our own state file
    }
    
    def __init__(self, 
                 excludes: Optional[Set[str]] = None,
                 min_size: int = 1,
                 max_size: Optional[int] = None,
                 follow_symlinks: bool = False):
        self.excludes = excludes or self.DEFAULT_EXCLUDES
        self.min_size = min_size
        self.max_size = max_size
        self.follow_symlinks = follow_symlinks
    
    def traverse(self, path: str) -> Iterator[Tuple[str, int, float]]:
        """Yield (filepath, size, mtime) for all matching files."""
        root_path = Path(path).resolve()
        
        if root_path.is_file():
            stat = root_path.stat()
            if self._should_include(stat.st_size):
                yield str(root_path), stat.st_size, stat.st_mtime
            return
        
        for entry in root_path.rglob('*'):
            try:
                # Skip excluded directories
                if any(part in self.excludes for part in entry.parts):
                    continue
                
                if not entry.is_file():
                    continue
                
                stat = entry.stat()
                size = stat.st_size
                
                if not self._should_include(size):
                    continue
                
                yield str(entry), size, stat.st_mtime
                
            except (OSError, PermissionError):
                continue
    
    def _should_include(self, size: int) -> bool:
        """Check if file size passes filters."""
        if size < self.min_size:
            return False
        if self.max_size is not None and size > self.max_size:
            return False
        return True

# ============================================================================
# Duplicate Detector
# ============================================================================

class DuplicateDetector:
    """Main engine for detecting duplicate files."""
    
    def __init__(self, 
                 state_db: Optional[StateDatabase] = None,
                 use_chunking: bool = True,
                 verbose: bool = False):
        self.state_db = state_db or StateDatabase()
        self.use_chunking = use_chunking
        self.verbose = verbose
        self.hasher = HashEngine()
    
    def scan(self, 
             path: str,
             traverser: FileTraverser,
             progress: bool = True) -> List[DuplicateGroup]:
        """Scan directory for duplicates."""
        
        # Phase 1: Collect all files
        if RICH_AVAILABLE and progress:
            with console.status("[bold green]Discovering files..."):
                files = list(traverser.traverse(path))
        else:
            files = list(traverser.traverse(path))
            if self.verbose:
                print(f"Found {len(files)} files to analyze")
        
        if not files:
            return []
        
        # Phase 2: Quick hash (first 4KB) with incremental support
        file_infos = self._phase_quick_hash(files, progress)
        
        # Phase 3: Group by quick hash and size
        candidates = self._find_candidates(file_infos)
        
        if not candidates:
            return []
        
        # Phase 4: Full hash verification
        duplicates = self._phase_full_verify(candidates, progress)
        
        return duplicates
    
    def _phase_quick_hash(self, 
                          files: List[Tuple[str, int, float]],
                          progress: bool) -> List[FileInfo]:
        """Compute quick hashes with caching."""
        file_infos = []
        cached_count = 0
        
        iterator = files
        if RICH_AVAILABLE and progress:
            progress_ctx = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            )
        else:
            progress_ctx = None
        
        def process_file(args):
            nonlocal cached_count
            filepath, size, mtime = args
            
            # Check cache first
            cached = self.state_db.get_cached(filepath, mtime, size)
            if cached:
                cached_count += 1
                return cached
            
            # Compute quick hash
            qhash = self.hasher.quick_hash(filepath)
            info = FileInfo(filepath, size, mtime, qhash)
            self.state_db.update(info)
            return info
        
        if progress_ctx:
            with progress_ctx as prog:
                task = prog.add_task("Quick hashing...", total=len(files))
                for args in files:
                    file_infos.append(process_file(args))
                    prog.advance(task)
        else:
            for args in files:
                file_infos.append(process_file(args))
        
        if self.verbose:
            print(f"  Quick hash: {len(file_infos)} files, {cached_count} from cache")
        
        return file_infos
    
    def _find_candidates(self, file_infos: List[FileInfo]) -> List[List[FileInfo]]:
        """Group files by size and quick hash to find candidates."""
        # Group by (size, quick_hash)
        groups = defaultdict(list)
        for info in file_infos:
            key = (info.size, info.quick_hash)
            groups[key].append(info)
        
        # Return only groups with multiple files
        return [group for group in groups.values() if len(group) > 1]
    
    def _phase_full_verify(self,
                           candidates: List[List[FileInfo]],
                           progress: bool) -> List[DuplicateGroup]:
        """Verify duplicates with full hash or chunk comparison."""
        duplicates = []
        
        iterator = candidates
        if RICH_AVAILABLE and progress:
            progress_ctx = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            )
        else:
            progress_ctx = None
        
        def verify_group(group: List[FileInfo]) -> Optional[DuplicateGroup]:
            """Verify a group of potential duplicates."""
            if len(group) < 2:
                return None
            
            size = group[0].size
            
            # For small files, use full hash
            # For large files, use chunk comparison if enabled
            hash_groups = defaultdict(list)
            
            for info in group:
                if info.full_hash:
                    hash_groups[info.full_hash].append(info.path)
                elif size < LARGE_FILE_THRESHOLD or not self.use_chunking:
                    full_hash = self.hasher.full_hash(info.path)
                    self.state_db.update_full_hash(info.path, full_hash)
                    hash_groups[full_hash].append(info.path)
                else:
                    # Large file - compare with first file chunk by chunk
                    first_path = group[0].path
                    if self.hasher.chunked_compare(first_path, info.path):
                        # Use the first file's hash as group key
                        if group[0].full_hash:
                            key = group[0].full_hash
                        else:
                            key = self.hasher.full_hash(first_path)
                            self.state_db.update_full_hash(first_path, key)
                            group[0].full_hash = key
                        hash_groups[key].append(info.path)
                    else:
                        # Different despite same quick hash (collision)
                        pass
            
            # Find groups with actual duplicates
            for hash_val, paths in hash_groups.items():
                if len(paths) > 1:
                    return DuplicateGroup(size=size, hash=hash_val, files=paths)
            
            return None
        
        if progress_ctx:
            with progress_ctx as prog:
                task = prog.add_task("Verifying duplicates...", total=len(candidates))
                for group in candidates:
                    result = verify_group(group)
                    if result:
                        duplicates.append(result)
                    prog.advance(task)
        else:
            for group in candidates:
                result = verify_group(group)
                if result:
                    duplicates.append(result)
        
        return duplicates

# ============================================================================
# Clean Command
# ============================================================================

class Cleaner:
    """Handle cleanup of duplicate files."""
    
    KEEP_STRATEGIES = ['first', 'newest', 'oldest', 'largest', 'smallest']
    
    def __init__(self, dry_run: bool = True, 
                 keep_strategy: str = 'first',
                 trash_dir: Optional[str] = None):
        self.dry_run = dry_run
        self.keep_strategy = keep_strategy
        self.trash_dir = trash_dir
        self.deleted_count = 0
        self.freed_bytes = 0
    
    def clean(self, duplicates: List[DuplicateGroup]) -> dict:
        """Clean duplicates according to strategy."""
        results = {
            'groups_processed': 0,
            'files_deleted': 0,
            'bytes_freed': 0,
            'errors': []
        }
        
        for group in duplicates:
            try:
                to_delete = self._select_for_deletion(group)
                
                for filepath in to_delete:
                    if self.dry_run:
                        results['files_deleted'] += 1
                        results['bytes_freed'] += group.size
                    else:
                        if self._delete_file(filepath):
                            results['files_deleted'] += 1
                            results['bytes_freed'] += group.size
                        else:
                            results['errors'].append(filepath)
                
                results['groups_processed'] += 1
                
            except Exception as e:
                results['errors'].append(f"{group.hash}: {e}")
        
        return results
    
    def _select_for_deletion(self, group: DuplicateGroup) -> List[str]:
        """Select which files to delete based on strategy."""
        files = group.files.copy()
        
        if self.keep_strategy == 'first':
            keep = files[0]
        elif self.keep_strategy == 'newest':
            files_by_mtime = [(f, os.path.getmtime(f)) for f in files]
            files_by_mtime.sort(key=lambda x: x[1], reverse=True)
            keep = files_by_mtime[0][0]
        elif self.keep_strategy == 'oldest':
            files_by_mtime = [(f, os.path.getmtime(f)) for f in files]
            files_by_mtime.sort(key=lambda x: x[1])
            keep = files_by_mtime[0][0]
        elif self.keep_strategy == 'largest':
            # All same size in a duplicate group, keep first
            keep = files[0]
        elif self.keep_strategy == 'smallest':
            keep = files[0]
        else:
            keep = files[0]
        
        return [f for f in files if f != keep]
    
    def _delete_file(self, filepath: str) -> bool:
        """Delete or move to trash."""
        try:
            if self.trash_dir:
                os.makedirs(self.trash_dir, exist_ok=True)
                dest = os.path.join(self.trash_dir, os.path.basename(filepath))
                # Handle name collision
                counter = 1
                while os.path.exists(dest):
                    name, ext = os.path.splitext(os.path.basename(filepath))
                    dest = os.path.join(self.trash_dir, f"{name}_{counter}{ext}")
                    counter += 1
                os.rename(filepath, dest)
            else:
                os.remove(filepath)
            return True
        except OSError:
            return False

# ============================================================================
# CLI Commands
# ============================================================================

def cmd_scan(args):
    """Execute scan command."""
    path = os.path.abspath(args.path)
    
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return 1
    
    # Setup components
    state_db = StateDatabase(args.state_db) if not args.no_incremental else None
    traverser = FileTraverser(
        excludes=set(args.exclude) if args.exclude else None,
        min_size=args.min_size,
        max_size=args.max_size,
        follow_symlinks=args.follow_symlinks
    )
    detector = DuplicateDetector(
        state_db=state_db,
        use_chunking=not args.no_chunking,
        verbose=args.verbose
    )
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold blue]Scanning:[/] {path}\n"
            f"[dim]Incremental: {state_db is not None} | "
            f"Chunking: {not args.no_chunking}[/dim]"
        ))
    else:
        print(f"Scanning: {path}")
    
    # Run scan
    start_time = datetime.now()
    duplicates = detector.scan(path, traverser, progress=not args.no_progress)
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # Display results
    if not duplicates:
        if RICH_AVAILABLE:
            console.print("[bold green]✓ No duplicates found![/]")
        else:
            print("No duplicates found!")
        return 0
    
    # Calculate stats
    total_duplicates = sum(len(d.files) - 1 for d in duplicates)
    total_wasted = sum(d.wasted_space for d in duplicates)
    
    if RICH_AVAILABLE:
        table = Table(title=f"Found {len(duplicates)} Duplicate Groups")
        table.add_column("Group", style="cyan")
        table.add_column("Size", justify="right", style="green")
        table.add_column("Files", justify="right")
        table.add_column("Wasted", justify="right", style="red")
        table.add_column("Sample Files", style="dim")
        
        for i, dup in enumerate(duplicates, 1):
            size_str = format_bytes(dup.size)
            wasted_str = format_bytes(dup.wasted_space)
            sample = dup.files[0][:50] + "..." if len(dup.files[0]) > 50 else dup.files[0]
            table.add_row(
                str(i),
                size_str,
                str(len(dup.files)),
                wasted_str,
                sample
            )
        
        console.print(table)
        console.print(f"\n[bold]Total duplicates:[/] {total_duplicates}")
        console.print(f"[bold red]Wasted space:[/] {format_bytes(total_wasted)}")
        console.print(f"[dim]Scan completed in {elapsed:.2f}s[/dim]")
    else:
        print(f"\nFound {len(duplicates)} duplicate groups")
        print(f"Total duplicates: {total_duplicates}")
        print(f"Wasted space: {format_bytes(total_wasted)}")
        
        if args.verbose:
            for i, dup in enumerate(duplicates, 1):
                print(f"\nGroup {i}: {format_bytes(dup.size)} each, {len(dup.files)} files")
                for f in dup.files[:5]:
                    print(f"  - {f}")
                if len(dup.files) > 5:
                    print(f"  ... and {len(dup.files) - 5} more")
    
    # Save results if requested
    if args.output:
        output_data = {
            'scan_path': path,
            'scan_time': start_time.isoformat(),
            'elapsed_seconds': elapsed,
            'total_groups': len(duplicates),
            'total_duplicates': total_duplicates,
            'wasted_bytes': total_wasted,
            'duplicates': [
                {'size': d.size, 'hash': d.hash, 'files': d.files}
                for d in duplicates
            ]
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        if not RICH_AVAILABLE or args.verbose:
            print(f"\nResults saved to: {args.output}")
    
    return 0

def cmd_clean(args):
    """Execute clean command."""
    # Load scan results or scan now
    if args.input:
        with open(args.input, 'r') as f:
            data = json.load(f)
        duplicates = [
            DuplicateGroup(d['size'], d['hash'], d['files'])
            for d in data['duplicates']
        ]
    else:
        # Run scan first
        if not args.path:
            print("Error: --path required when not using --input", file=sys.stderr)
            return 1
        
        state_db = StateDatabase(args.state_db) if not args.no_incremental else None
        traverser = FileTraverser(min_size=args.min_size)
        detector = DuplicateDetector(state_db=state_db)
        duplicates = detector.scan(args.path, traverser)
    
    if not duplicates:
        print("No duplicates to clean.")
        return 0
    
    # Setup cleaner
    cleaner = Cleaner(
        dry_run=args.dry_run,
        keep_strategy=args.keep,
        trash_dir=args.trash_dir
    )
    
    if args.dry_run:
        if RICH_AVAILABLE:
            console.print("[bold yellow]⚠ DRY RUN MODE - No files will be deleted[/]")
        else:
            print("=== DRY RUN MODE - No files will be deleted ===")
    
    results = cleaner.clean(duplicates)
    
    if RICH_AVAILABLE:
        status = "[bold yellow]Would delete" if args.dry_run else "[bold red]Deleted"
        console.print(f"\n{status}:[/] {results['files_deleted']} files")
        console.print(f"[bold]{status} space:[/] {format_bytes(results['bytes_freed'])}")
        
        if results['errors']:
            console.print(f"[bold red]Errors: {len(results['errors'])}[/]")
    else:
        action = "Would delete" if args.dry_run else "Deleted"
        print(f"\n{action}: {results['files_deleted']} files")
        print(f"{action} space: {format_bytes(results['bytes_freed'])}")
        
        if results['errors'] and args.verbose:
            print("\nErrors:")
            for err in results['errors']:
                print(f"  - {err}")
    
    return 0

def cmd_stats(args):
    """Show database statistics."""
    db = StateDatabase(args.state_db)
    stats = db.get_stats()
    
    if RICH_AVAILABLE:
        console.print(Panel.fit(
            f"[bold]State Database Statistics[/bold]\n\n"
            f"Total files tracked: {stats['total']}\n"
            f"Files with full hash: {stats['with_full_hash']}\n"
            f"Database location: {args.state_db}"
        ))
    else:
        print(f"State Database: {args.state_db}")
        print(f"Total files tracked: {stats['total']}")
        print(f"Files with full hash: {stats['with_full_hash']}")
    
    return 0

# ============================================================================
# Utilities
# ============================================================================

def format_bytes(size: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        prog='dedupe',
        description='File Deduplication Tool - Like mini rsync',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    dedupe scan ./photos              # Scan directory for duplicates
    dedupe scan ./docs --min-size 1M  # Only check files > 1MB
    dedupe clean --dry-run            # Preview what would be deleted
    dedupe clean --keep newest        # Keep newest, delete rest
    dedupe clean --trash-dir ./trash  # Move to trash instead of delete
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan for duplicate files')
    scan_parser.add_argument('path', help='Directory or file to scan')
    scan_parser.add_argument('-o', '--output', help='Save results to JSON file')
    scan_parser.add_argument('--min-size', type=int, default=1,
                            help='Minimum file size in bytes (default: 1)')
    scan_parser.add_argument('--max-size', type=int,
                            help='Maximum file size in bytes')
    scan_parser.add_argument('--exclude', action='append',
                            help='Directory names to exclude (can use multiple)')
    scan_parser.add_argument('--follow-symlinks', action='store_true',
                            help='Follow symbolic links')
    scan_parser.add_argument('--no-incremental', action='store_true',
                            help='Disable incremental scanning')
    scan_parser.add_argument('--no-chunking', action='store_true',
                            help='Disable chunk-based comparison for large files')
    scan_parser.add_argument('--no-progress', action='store_true',
                            help='Disable progress bars')
    scan_parser.add_argument('-v', '--verbose', action='store_true',
                            help='Verbose output')
    scan_parser.add_argument('--state-db', default=STATE_DB_NAME,
                            help='State database path')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean duplicate files')
    clean_parser.add_argument('--input', '-i', help='Use scan results from JSON file')
    clean_parser.add_argument('--path', help='Directory to scan and clean')
    clean_parser.add_argument('--dry-run', action='store_true', default=True,
                             help='Preview without deleting (default: true)')
    clean_parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                             help='Actually delete files')
    clean_parser.add_argument('--keep', default='first',
                             choices=Cleaner.KEEP_STRATEGIES,
                             help='Which file to keep (default: first)')
    clean_parser.add_argument('--trash-dir',
                             help='Move files to trash directory instead of deleting')
    clean_parser.add_argument('--min-size', type=int, default=1)
    clean_parser.add_argument('--no-incremental', action='store_true')
    clean_parser.add_argument('--state-db', default=STATE_DB_NAME)
    clean_parser.add_argument('-v', '--verbose', action='store_true')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show state database statistics')
    stats_parser.add_argument('--state-db', default=STATE_DB_NAME)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command handler
    commands = {
        'scan': cmd_scan,
        'clean': cmd_clean,
        'stats': cmd_stats,
    }
    
    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as e:
        if args.verbose if hasattr(args, 'verbose') else False:
            raise
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
