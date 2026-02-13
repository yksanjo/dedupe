"""Tests for HashEngine class."""

import pytest
import tempfile
import os
from pathlib import Path

from dedupe import HashEngine


class TestHashEngine:
    """Test cases for HashEngine."""
    
    def test_quick_hash_same_content(self):
        """Files with same content should have same quick hash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("test content")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write("test content")
            path2 = f2.name
        
        try:
            hash1 = HashEngine.quick_hash(path1)
            hash2 = HashEngine.quick_hash(path2)
            
            assert hash1 == hash2
            assert len(hash1) == 32  # 16 bytes hex = 32 chars
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_quick_hash_different_content(self):
        """Files with different content should have different hashes."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("content A")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write("content B")
            path2 = f2.name
        
        try:
            hash1 = HashEngine.quick_hash(path1)
            hash2 = HashEngine.quick_hash(path2)
            
            assert hash1 != hash2
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_quick_hash_large_file(self):
        """Quick hash only reads first 4KB."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write 8KB of data
            f.write(b"A" * 4096)
            f.write(b"B" * 4096)
            path = f.name
        
        try:
            hash_result = HashEngine.quick_hash(path)
            assert len(hash_result) == 32
        finally:
            os.unlink(path)
    
    def test_quick_hash_nonexistent_file(self):
        """Should return empty string for nonexistent file."""
        result = HashEngine.quick_hash("/nonexistent/path/file.txt")
        assert result == ""
    
    def test_full_hash_same_content(self):
        """Files with same content should have same full hash."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f1:
            f1.write("full content test")
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f2:
            f2.write("full content test")
            path2 = f2.name
        
        try:
            hash1 = HashEngine.full_hash(path1)
            hash2 = HashEngine.full_hash(path2)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # 32 bytes hex = 64 chars
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_full_hash_vs_quick_hash_different(self):
        """Full and quick hashes should be different."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content for hash comparison")
            path = f.name
        
        try:
            quick = HashEngine.quick_hash(path)
            full = HashEngine.full_hash(path)
            
            assert quick != full
            assert len(quick) == 32
            assert len(full) == 64
        finally:
            os.unlink(path)
    
    def test_chunked_compare_identical_files(self):
        """Chunked compare should return True for identical files."""
        content = b"chunk test content" * 1000  # ~18KB
        
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(content)
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(content)
            path2 = f2.name
        
        try:
            result = HashEngine.chunked_compare(path1, path2)
            assert result is True
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_chunked_compare_different_files(self):
        """Chunked compare should return False for different files."""
        with tempfile.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"A" * 10000)
            path1 = f1.name
        
        with tempfile.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"B" * 10000)
            path2 = f2.name
        
        try:
            result = HashEngine.chunked_compare(path1, path2)
            assert result is False
        finally:
            os.unlink(path1)
            os.unlink(path2)
    
    def test_chunked_compare_nonexistent_file(self):
        """Should return False if either file doesn't exist."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            path = f.name
        
        try:
            result = HashEngine.chunked_compare(path, "/nonexistent")
            assert result is False
        finally:
            os.unlink(path)
