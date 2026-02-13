"""Tests for StateDatabase class."""

import pytest
import tempfile
import os
from pathlib import Path

from dedupe import StateDatabase, FileInfo


class TestStateDatabase:
    """Test cases for StateDatabase."""
    
    def test_init_creates_database(self):
        """Should create SQLite database on init."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir, "test.db")
            db = StateDatabase(str(db_path))
            
            assert db_path.exists()
    
    def test_update_and_get_cached(self):
        """Should store and retrieve file info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            
            info = FileInfo(
                path="/test/file.txt",
                size=100,
                mtime=1234567890.0,
                quick_hash="abc123",
                full_hash="def456"
            )
            
            db.update(info)
            
            # Retrieve with matching mtime/size
            cached = db.get_cached("/test/file.txt", 1234567890.0, 100)
            
            assert cached is not None
            assert cached.path == "/test/file.txt"
            assert cached.quick_hash == "abc123"
            assert cached.full_hash == "def456"
    
    def test_get_cached_returns_none_on_mismatch(self):
        """Should return None if mtime or size changed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            
            info = FileInfo(
                path="/test/file.txt",
                size=100,
                mtime=1234567890.0,
                quick_hash="abc123"
            )
            db.update(info)
            
            # Different mtime
            cached = db.get_cached("/test/file.txt", 9999999999.0, 100)
            assert cached is None
            
            # Different size
            cached = db.get_cached("/test/file.txt", 1234567890.0, 999)
            assert cached is None
    
    def test_update_full_hash(self):
        """Should update full hash separately."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            
            info = FileInfo(
                path="/test/file.txt",
                size=100,
                mtime=1234567890.0,
                quick_hash="abc123",
                full_hash=None
            )
            db.update(info)
            
            db.update_full_hash("/test/file.txt", "fullhash123")
            
            cached = db.get_cached("/test/file.txt", 1234567890.0, 100)
            assert cached.full_hash == "fullhash123"
    
    def test_remove_missing(self):
        """Should remove entries for deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            
            # Add two files
            db.update(FileInfo("/test/file1.txt", 100, 1.0, "hash1"))
            db.update(FileInfo("/test/file2.txt", 200, 2.0, "hash2"))
            
            # Remove one from filesystem (simulated)
            removed = db.remove_missing({"/test/file1.txt"})
            
            assert removed == 1
            
            # file2 should be gone from cache
            cached = db.get_cached("/test/file2.txt", 2.0, 200)
            assert cached is None
    
    def test_get_stats(self):
        """Should return database statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            
            db.update(FileInfo("/test/file1.txt", 100, 1.0, "hash1", "full1"))
            db.update(FileInfo("/test/file2.txt", 200, 2.0, "hash2"))
            
            stats = db.get_stats()
            
            assert stats["total"] == 2
            assert stats["with_full_hash"] == 1
    
    def test_thread_safety(self):
        """Should handle concurrent access."""
        import threading
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db = StateDatabase(str(Path(tmpdir, "test.db")))
            errors = []
            
            def worker(n):
                try:
                    info = FileInfo(f"/test/file{n}.txt", n, float(n), f"hash{n}")
                    db.update(info)
                    db.get_cached(f"/test/file{n}.txt", float(n), n)
                except Exception as e:
                    errors.append(e)
            
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            assert len(errors) == 0
            stats = db.get_stats()
            assert stats["total"] == 10
