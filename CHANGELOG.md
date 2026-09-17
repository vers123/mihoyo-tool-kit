# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-18

First stable release. Version number reset from 5.0.0 to 1.0.0.

### Release Highlights

- **40 CLI functions** across 9 groups, plus PySide6 GUI
- **TXT filter** with exact/fuzzy matching, preview dialog, and time-based renumbering
- **Weibo full pagination** via `since_id` cursor — fetches all posts back to 2019
- **Native GUI style** (PySide6 platform style) with application icon
- **Build system**: PyInstaller EXE, Docker (cli/full), GitHub Actions CI/CD
- **Cleanup**: CLI + build script cache cleaning with confirmation

### Added
- **GUI window icon**: application icon (`resources/icon/app.ico`, multi-size 16/32/48/64/128/256).
- **TXT filter preview**: GUI preview dialog with table view (new index, original index, title, date, category, matched keywords, source file) and confirm/modify/cancel actions.
- **TXT filter match modes**: exact (full substring) and fuzzy (2-gram fragment) matching, selectable in both CLI and GUI.
- **TQDM progress bars**: weibo, news, user posts, custom scraper now show live progress.
- **Build system**: PyInstaller spec (`app.spec`), version metadata (`version_info.txt`), cross-platform build scripts (`build.ps1`/`build.bat`/`build.sh`), Docker dual-mode (`cli`/`full`), GitHub Actions CI/CD.
- **Cleanup**: CLI menu option 40 and build script `clean` command, both require `YES` confirmation.
- **CHANGELOG.md**: version history document.

### Changed
- **GUI style**: switched from custom `LIGHT_QSS` theme to PySide6 native platform style. Font utilities moved to `gui/fonts.py`.
- **TXT filter keyword logic**: changed from AND to OR (any keyword hits).
- **Version**: reset from `5.0.0` to `1.0.0`.

### Fixed
- **Weibo scraper**: `bid` field no longer returned by API; now uses `mblogid` (with fallback to `bid`/`mid`/`idstr`).
- **Weibo pagination**: use API `since_id` cursor instead of `page`-only to reach the earliest posts.
- **Weibo date parsing**: support English format `Tue Dec 31 12:04:22 +0800 2019` → `YYYY-MM-DD HH:MM:SS`.
- **Pagination limits**: removed artificial `max_pages` / `max_scrolls` caps across all scrapers; rely on API/scroll termination signals.
- **Cross-drive path**: `os.path.relpath` failure on different drives handled gracefully.

### Removed
- `gui/theme.py` (custom QSS theme).

---

## [5.0.0] - (previous)

### Changed
- News storage moved to SQLite (`data/news.db`); data files retained for human reading.
- Auto-migration of pre-V5 filenames via `utils/migration.py`.
- 7-field `NewsItem` introduced; 4-field legacy read-only.

### Added
- Non-interactive CLI path: `--fetch` / `--export-excel` / `--count` + `core/api_client.py`.

---

## Pre-V5

- Flat `data/` layout, single news file per site, no SQLite, no GUI.
