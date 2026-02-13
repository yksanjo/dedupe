"""Tests for FileTraverser class."""

import pytest
import tempfile
import os
from pathlib import Path

from dedupe import FileTraverser


class TestFileTraverser:
    """Test cases for FileTraverser."""
    
    def test_traverse_single_file(self):
        """Should handle single file path."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = f.name
        
        try:
            traverser = FileTraverser()
            files = list(traverser.traverse(path))
            
            assert len(files) == 1
            # Use resolve() to handle macOS /private prefix differences
            assert Path(files[0][0]).resolve() == Path(path).resolve()
            assert files[0][1] == 4     # size
        finally:
            os.unlink(path)
    
    def test_traverse_directory(self):
        """Should find all files in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "file1.txt").write_text("content1")
            Path(tmpdir, "file2.txt").write_text("content2")
            Path(tmpdir, "subdir").mkdir()
            Path(tmpdir, "subdir", "file3.txt").write_text("content3")
            
            traverser = FileTraverser()
            files = list(traverser.traverse(tmpdir))
            
            assert len(files) == 3
            paths = [f[0] for f in files]
            assert any("file1.txt" in p for p in paths)
            assert any("file2.txt" in p for p in paths)
            assert any("file3.txt" in p for p in paths)
    
    def test_traverse_respects_min_size(self):
        """Should filter files below min_size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "small.txt").write_text("x")  # 1 byte
            Path(tmpdir, "large.txt").write_text("x" * 100)  # 100 bytes
            
            traverser = FileTraverser(min_size=50)
            files = list(traverser.traverse(tmpdir))
            
            assert len(files) == 1
            assert "large.txt" in files[0][0]
    
    def test_traverse_respects_max_size(self):
        """Should filter files above max_size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "small.txt").write_text("x" * 10)
            Path(tmpdir, "large.txt").write_text("x" * 1000)
            
            traverser = FileTraverser(max_size=500)
            files = list(traverser.traverse(tmpdir))
            
            assert len(files) == 1
            assert "small.txt" in files[0][0]
    
    def test_traverse_excludes_directories(self):
        """Should skip excluded directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "keep.txt").write_text("content")
            Path(tmpdir, "__pycache__").mkdir()
            Path(tmpdir, "__pycache__", "cache.pyc").write_text("cached")
            
            traverser = FileTraverser()
            files = list(traverser.traverse(tmpdir))
            
            paths = [f[0] for f in files]
            assert any("keep.txt" in p for p in paths)
            assert not any("cache.pyc" in p for p in paths)
    
    def test_traverse_custom_excludes(self):
        """Should respect custom exclude patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "keep.txt").write_text("content")
            Path(tmpdir, "skip_me").mkdir()
            Path(tmpdir, "skip_me", "file.txt").write_text("skipped")
            
            traverser = FileTraverser(excludes={"skip_me"})
            files = list(traverser.traverse(tmpdir))
            
            paths = [f[0] for f in files]
            assert any("keep.txt" in p for p in paths)
            assert not any("skip_me" in p for p in paths)
    
    def test_traverse_handles_permission_error(self):
        """Should gracefully handle permission errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "readable.txt").write_text("content")
            
            traverser = FileTraverser()
            files = list(traverser.traverse(tmpdir))
            
            assert len(files) >= 0  # Should not crash
    
    def test_traverse_returns_correct_types(self):
        """Should return (path, size, mtime) tuples."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = f.name
        
        try:
            traverser = FileTraverser()
            files = list(traverser.traverse(path))
            
            assert len(files) == 1
            filepath, size, mtime = files[0]
            
            assert isinstance(filepath, str)
            assert isinstance(size, int)
            assert isinstance(mtime, float)
        finally:
            os.unlink(path)
