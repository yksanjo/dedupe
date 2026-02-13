"""Tests for Cleaner class."""

import pytest
import tempfile
import os
from pathlib import Path

from dedupe import Cleaner, DuplicateGroup


class TestCleaner:
    """Test cases for Cleaner."""
    
    def test_dry_run_does_not_delete(self):
        """Dry run should not actually delete files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "file1.txt")
            file2 = Path(tmpdir, "file2.txt")
            file1.write_text("duplicate content")
            file2.write_text("duplicate content")
            
            cleaner = Cleaner(dry_run=True)
            duplicates = [DuplicateGroup(
                size=18,
                hash="abc123",
                files=[str(file1), str(file2)]
            )]
            
            results = cleaner.clean(duplicates)
            
            # Files should still exist
            assert file1.exists()
            assert file2.exists()
            assert results["files_deleted"] == 1  # But counted
    
    def test_actually_deletes_with_no_dry_run(self):
        """Should delete when dry_run=False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "file1.txt")
            file2 = Path(tmpdir, "file2.txt")
            file1.write_text("duplicate content")
            file2.write_text("duplicate content")
            
            cleaner = Cleaner(dry_run=False, keep_strategy="first")
            duplicates = [DuplicateGroup(
                size=18,
                hash="abc123",
                files=[str(file1), str(file2)]
            )]
            
            results = cleaner.clean(duplicates)
            
            # First kept, second deleted
            assert file1.exists()
            assert not file2.exists()
            assert results["files_deleted"] == 1
    
    def test_keep_first_strategy(self):
        """Should keep first file in list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            files = []
            for i in range(3):
                f = Path(tmpdir, f"file{i}.txt")
                f.write_text("content")
                files.append(str(f))
            
            cleaner = Cleaner(dry_run=False, keep_strategy="first")
            duplicates = [DuplicateGroup(size=7, hash="abc", files=files)]
            
            cleaner.clean(duplicates)
            
            assert Path(files[0]).exists()  # First kept
            assert not Path(files[1]).exists()  # Others deleted
            assert not Path(files[2]).exists()
    
    def test_keep_newest_strategy(self):
        """Should keep newest file by mtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "old.txt")
            file2 = Path(tmpdir, "new.txt")
            file1.write_text("content")
            file2.write_text("content")
            
            # Set old mtime
            old_time = 1000000000
            os.utime(file1, (old_time, old_time))
            
            cleaner = Cleaner(dry_run=False, keep_strategy="newest")
            duplicates = [DuplicateGroup(
                size=7,
                hash="abc",
                files=[str(file1), str(file2)]
            )]
            
            cleaner.clean(duplicates)
            
            assert not file1.exists()  # Old deleted
            assert file2.exists()  # New kept
    
    def test_keep_oldest_strategy(self):
        """Should keep oldest file by mtime."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "old.txt")
            file2 = Path(tmpdir, "new.txt")
            file1.write_text("content")
            file2.write_text("content")
            
            # Set old mtime
            old_time = 1000000000
            os.utime(file1, (old_time, old_time))
            
            cleaner = Cleaner(dry_run=False, keep_strategy="oldest")
            duplicates = [DuplicateGroup(
                size=7,
                hash="abc",
                files=[str(file1), str(file2)]
            )]
            
            cleaner.clean(duplicates)
            
            assert file1.exists()  # Old kept
            assert not file2.exists()  # New deleted
    
    def test_move_to_trash(self):
        """Should move files to trash directory instead of deleting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "keep.txt")
            file2 = Path(tmpdir, "delete.txt")
            file1.write_text("content")
            file2.write_text("content")
            
            trash_dir = Path(tmpdir, "trash")
            
            cleaner = Cleaner(dry_run=False, trash_dir=str(trash_dir))
            duplicates = [DuplicateGroup(
                size=7,
                hash="abc",
                files=[str(file1), str(file2)]
            )]
            
            cleaner.clean(duplicates)
            
            assert file1.exists()  # Kept in place
            assert not file2.exists()  # Moved from original
            assert (trash_dir / "delete.txt").exists()  # In trash
    
    def test_wasted_space_calculation(self):
        """DuplicateGroup should calculate wasted space correctly."""
        group = DuplicateGroup(
            size=100,
            hash="abc",
            files=["a", "b", "c", "d"]  # 4 files
        )
        
        # Should be size * (count - 1) = 100 * 3 = 300
        assert group.wasted_space == 300
    
    def test_empty_duplicates_list(self):
        """Should handle empty duplicates list."""
        cleaner = Cleaner(dry_run=True)
        results = cleaner.clean([])
        
        assert results["groups_processed"] == 0
        assert results["files_deleted"] == 0
    
    def test_single_file_group(self):
        """Should skip groups with only one file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir, "only.txt")
            file1.write_text("content")
            
            cleaner = Cleaner(dry_run=False)
            duplicates = [DuplicateGroup(
                size=7,
                hash="abc",
                files=[str(file1)]
            )]
            
            results = cleaner.clean(duplicates)
            
            assert file1.exists()  # Not deleted
            assert results["files_deleted"] == 0
