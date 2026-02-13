# dedupe

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/yksanjo/dedupe/actions/workflows/ci.yml/badge.svg)](https://github.com/yksanjo/dedupe/actions)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A high-performance file deduplication tool with incremental scanning — like mini rsync for finding and cleaning duplicate files.

## ✨ Features

- 🚀 **Fast Hashing** — Uses BLAKE2b (faster than MD5/SHA256) with two-phase approach
- 📦 **Incremental Scanning** — SQLite-backed state database skips unchanged files
- 🧠 **Smart Memory Usage** — Chunk-based comparison for large files (>100MB)
- 🛡️ **Safe by Default** — Dry-run mode; never deletes without explicit confirmation
- 📊 **Beautiful Output** — Rich progress bars and tables (falls back to plain text)
- 🔧 **Flexible Cleanup** — Multiple keep strategies (first, newest, oldest)

## 🚀 Quick Start

```bash
# Scan a directory for duplicates
./dedupe scan ./photos

# Preview what would be deleted (safe)
./dedupe clean --dry-run

# Actually remove duplicates (keep first occurrence)
./dedupe clean --no-dry-run

# Keep newest file, move rest to trash
./dedupe clean --keep newest --trash-dir ./trash
```

## 📋 Installation

### Quick Install

```bash
# Download and install
curl -fsSL https://raw.githubusercontent.com/yksanjo/dedupe/main/install.sh | bash

# Or manually
git clone https://github.com/yksanjo/dedupe.git
cd dedupe
./install.sh
```

### Manual Install

```bash
git clone https://github.com/yksanjo/dedupe.git
cd dedupe
chmod +x dedupe
sudo ln -s $(pwd)/dedupe /usr/local/bin/dedupe
```

### Optional Dependencies

```bash
# For beautiful output (recommended)
pip install rich

# For development
make dev
```

## 📚 Commands

### `scan` — Find Duplicates

```bash
./dedupe scan <path> [options]

Options:
  -o, --output FILE       Save results to JSON file
  --min-size BYTES        Minimum file size (default: 1)
  --max-size BYTES        Maximum file size
  --exclude DIR           Exclude directory (can use multiple)
  --follow-symlinks       Follow symbolic links
  --no-incremental        Disable incremental scanning
  --no-chunking           Disable chunk-based comparison
  --no-progress           Disable progress bars
  -v, --verbose           Verbose output
```

### `clean` — Remove Duplicates

```bash
./dedupe clean [options]

Options:
  -i, --input FILE        Use scan results from JSON file
  --path PATH             Directory to scan and clean
  --dry-run               Preview without deleting (default: true)
  --no-dry-run            Actually delete files
  --keep STRATEGY         Which file to keep: first|newest|oldest|largest|smallest
  --trash-dir DIR         Move to trash instead of deleting
```

### `stats` — Database Info

```bash
./dedupe stats           # Show state database statistics
```

## 🧠 How It Works

### Two-Phase Hashing

1. **Quick Hash**: Hash first 4KB of every file — fast filter for unique files
2. **Full Hash**: Only compute full hash for files with matching quick hashes

### Incremental Scanning

The tool maintains a SQLite database (`.dedupe_state.db`) that stores:
- File paths, sizes, and modification times
- Computed hashes

On rescan, unchanged files are skipped automatically — making subsequent scans nearly instant.

### Chunk-Based Comparison

For files larger than 100MB, instead of loading the entire file into memory:
- Reads and compares 8KB chunks sequentially
- Stops at first mismatch
- Memory usage stays constant regardless of file size

## 📊 Example Output

```
╭────────────────────────────────────╮
│ Scanning: /home/user/photos        │
│ Incremental: True | Chunking: True │
╰────────────────────────────────────╯
  Quick hashing... ━━━━━━━━━━━━━━━━━━ 100%
  Verifying duplicates... ━━━━━━━━━━━ 100%
                            Found 3 Duplicate Groups                            
┏━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Group ┃    Size ┃ Files ┃  Wasted ┃ Sample Files                         ┃
┡━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1     │  2.4 MB │     3 │  4.8 MB │ /photos/vacation/img_001.jpg         │
│ 2     │  856 KB │     2 │  856 KB │ /photos/backup/DSC_0422.png          │
│ 3     │  10.0 B │     5 │  40.0 B │ /photos/notes.txt                    │
└───────┴─────────┴───────┴─────────┴──────────────────────────────────────┘

Total duplicates: 7
Wasted space: 5.7 MB
Scan completed in 2.34s
```

## 🛠️ Technical Details

### Hash Algorithm: BLAKE2b

- **Faster than MD5** and more secure
- **Configurable digest size** — 16 bytes for quick hash, 32 bytes for full hash
- **Cryptographically secure** — negligible collision probability

### Performance

| Operation | 1,000 files | 10,000 files | 100,000 files |
|-----------|-------------|--------------|---------------|
| First scan | ~2s | ~15s | ~2min |
| Incremental | ~0.1s | ~0.5s | ~3s |
| Memory usage | ~10MB | ~50MB | ~200MB |

## 🔒 Safety Features

- **Dry-run by default** — Must explicitly use `--no-dry-run` to delete
- **Trash directory option** — Move instead of delete
- **Keep strategies** — Choose which duplicate to preserve
- **Permission checks** — Gracefully handles unreadable files

## 📝 License

MIT License — feel free to use, modify, and distribute.

## 🙏 Credits

Built as a learning project for:
- Hashing algorithms and performance
- Filesystem traversal optimization
- Incremental state management
- CLI design patterns

---

**Like this tool?** Give it a ⭐ on GitHub!
