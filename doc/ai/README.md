# miHoYo ToolKit — AI Agent Reference

> **Audience**: AI coding assistants and automated code agents (Trae, Cursor, Copilot, Claude Code, etc.).
> **Purpose**: Give an AI agent everything it needs to **read, navigate, modify, debug, and refactor** this codebase safely, without first requiring a human-guided tour.
> **Status**: Source of truth for machine consumption. The human-facing [README.md](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/README.md) is a subset of this information; when they conflict, the code wins, then this document, then the human README.
> **Project version**: 1.0.1 · **Last updated**: 2026-09-18

---

## 0. Quick Facts (read this first)

| Field | Value |
| --- | --- |
| Project name | miHoYo ToolKit / 米游社工具箱 |
| Version | 1.0.1 |
| Language | Python 3.8+ |
| Core deps | Playwright ≥1.40 · PySide6 ≥6.5 · httpx ≥0.27 · tenacity ≥8.2 · pydantic ≥2.0 · openpyxl ≥3.1 · tqdm ≥4.65 · Pillow ≥10.0 |
| Entry point | [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) |
| Run modes | Interactive CLI (default) · GUI (`--gui`) · Non-interactive API direct (`--fetch`, `--export-excel`, `--count`) |
| Config file | [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json) (configuration-driven) |
| License | MIT |
| OS target | Windows-first; macOS/Linux supported for non-GUI paths |
| Build/run container | [Dockerfile](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/Dockerfile) (non-interactive mode only) |

**One-line summary**: A Playwright-based scraper for miyoushe / hoyoverse news (Genshin CN/EN, ZZZ, Star Rail) + user posts + Weibo, with PySide6 GUI, Firefox-cookie auto-login, HAR fallback, incremental updates, SQLite storage, and Excel/RSS/JSON export.

---

## 1. How an AI agent should use this document

### 1.1 Read order per task type

| If the task is… | Read these sections in order |
| --- | --- |
| **Understand / navigate** "where is X" | §0 → §2 → §3 → §4 → §17 (file index) |
| **Modify / extend** (add a site, change a field) | §15 (constraints) → §4 (base contracts) → §10 (cookbook) → §6 (config) |
| **Debug / troubleshoot** | §12 (debug guide) → §8 (Cookie/HAR) → §13 (pitfalls) → §5 (data flow) |
| **Refactor / architecture change** | §15 → §2 (architecture) → §4 (contracts) → §14 (pre-flight) → §16 (compat) |

### 1.2 Non-negotiable: read §15 before any edit

Section §15 (AI Agent Hard Constraints) is binding. Violating a "Don't" there is treated as a bug even if the code still runs.

---

## 2. Architecture Overview

### 2.1 Layer diagram (text)

```
┌─────────────────────────────────────────────────────────────────┐
│  Entry: main.py  (argparse: --gui / --fetch / --export-excel)   │
└───────────────┬─────────────────────────────────┬───────────────┘
                │ interactive                       │ non-interactive
        ┌───────▼────────┐                 ┌───────▼────────┐
        │  CLI menu loop  │                 │  _run_cli()    │
        │  MiHoYoToolKit  │                 │  API direct    │
        └───────┬────────┘                 └───────┬────────┘
                │ dispatch to                       │ core.api_client
        ┌───────▼──────────────────────────────── ▼──────────────┐
        │  fetchers/   (Playwright + API intercept + Cookie/HAR)  │
        │  extractors/ (HTML → NewsItem; merge; dedup; export)   │
        └───────┬──────────────────────────────── ▲──────────────┘
                │                                     │
        ┌───────▼──────────┐         ┌──────────────▼────────────┐
        │  gui/ (PySide6)  │         │ core/                      │
        │  pages + workers │         │  scraper · api_client      │
        │  widgets · fonts │         │  storage · feed · models   │
        └──────────────────┘         │  config_manager            │
                                     └──────────────┬────────────┘
                                                    │
                                     ┌──────────────▼────────────┐
                                     │ utils/                     │
                                     │  cookie_loader · har_loader│
                                     │  backup_manager · logger   │
                                     │  error_handler · migration │
                                     └───────────────────────────┘
```

### 2.2 Module-level responsibility map

| Module | Path | Responsibility |
| --- | --- | --- |
| Entry | [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) | CLI menu, argparse, dispatch to `fetchers`/`extractors`/`gui`/`core.api_client`. Holds `MiHoYoToolKit` class with 39 numbered menu handlers. |
| Core | [core/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core) | Cross-cutting infra: scraper base, API client, SQLite storage, feed generation, config manager, data models. |
| Fetchers | [fetchers/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers) | Playwright-driven scrapers (news base + 4 site subclasses, user, weibo, baike, tutorial, custom). Exposes `run_*` functions. |
| Extractors | [extractors/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors) | HTML/JSON → structured `NewsItem`. News base + 4 subclasses, weibo, images, tutorial, excel_writer, txt_filter. Exposes `run_*` functions. |
| GUI | [gui/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui) | PySide6 app: `launch_gui()`, main_window, fonts (game fonts, reserved for settings), QThread workers, widgets, per-feature pages. Uses platform-native style (no custom QSS). |
| Utils | [utils/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils) | Firefox cookie loader, HAR loader, backup manager, error handler, migration, logger. |
| Resources | [resources/font/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/resources/font) · [resources/icon/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/resources/icon) | Game-specific fonts (HoYo-Glyphs) + application icon (`app.png` source, `app.ico` multi-size). See `resources/font/LICENSE`. |
| Tests | [tests/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests) | unittest suite + one integration script. |
| Data | `data/`, `logs/`, `har/` | Auto-created runtime outputs. Never check in. |

### 2.3 Key dependency directions

- `main.py` → `fetchers`, `extractors`, `gui`, `core` (lazy `import` inside handlers).
- `fetchers.news.*` → `core.scraper.BaseScraper`, `core.config_manager`, `utils.cookie_loader`, `utils.har_loader`.
- `extractors.news.*` → `core.storage` (for merge/dedup), `core.models`.
- `gui.pages.*` → `fetchers.run_*` and `extractors.run_*` via `_get_func()` indirection.
- `core.api_client` → `core.storage` (incremental dedup via `get_existing_urls`). Bypasses `fetchers` entirely (no Playwright).

---

## 3. Core Modules (responsibilities & key APIs)

### 3.1 `core/scraper.py` — `BaseScraper`
- Browser lifecycle, **API interception**, **Firefox cookie injection**, **HAR fallback**.
- `__init__(...)`: loads `ScraperConfig`, site config, incremental existing-URL set.
- Browser init + cookie inject: ~L52–84. When `use_firefox_cookies` is true and a target domain is set, calls `load_firefox_cookies()` and `context.add_cookies(...)`.
- API intercept + incremental stop + HAR fallback core: ~L84–161. Intercepts responses whose URL contains a configured keyword; in incremental mode, stops when an already-seen URL is encountered; on intercept failure, looks up `har/{scraper_name}/`.

### 3.2 `core/api_client.py` — `MiHoYoApiClient`
- Non-interactive API direct client (no Playwright, no TTY).
- `__init__(game_key, incremental=True, existing_urls=set())`: ~L41–67.
- `fetch_all()`: ~L171–241. Paginates `content_v2_user`, extracts news items, honors `total` / max-page, supports incremental early-stop.
- Used by `_run_cli()` in [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) for `--fetch` and by Docker.

### 3.3 `core/storage.py` — `NewsStorage`
- SQLite persistence; **one table per game** (table name == game key).
- Schema (~L35–63): primary key `iInfoId`; columns mirror the 7-field `NewsItem` (`iInfoId, title, date, category, intro, poster_url, url`).
- Key methods (~L71–118):
  - `upsert_items(game, items) → int` — batch insert or update; returns count of newly inserted rows.
  - `get_existing_urls(game) → set[str]` — used for incremental dedup.
  - `count_all() → dict[str,int]` — per-game row counts.
- Context-manager (`with NewsStorage() as store:`); commits on exit.

### 3.4 `core/feed.py`
- `generate_rss_feed()` → writes `output/news_feed.xml` (RSS 2.0).
- `generate_json_feed()` → writes `output/news_feed.json` (JSON Feed).
- Reads from `NewsStorage` across all four games.

### 3.5 `core/config_manager.py`
- Singleton `config_manager`. Methods: `get(key, default)`, `set(key, value)`, `save_config()`, `load_config()`, `get_all_news_sites()`, `get_output_dir(kind)`, `get_news_output_dir(game_key, kind)`.
- Dot-path keys supported: `news_sites.genshin.data_filename`.
- Config path: [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json) at project root.

### 3.6 `core/models.py`
- pydantic v2 models. Defines `NewsItem` and related dataclasses shared across fetchers/extractors/storage.

---

## 4. Base Class Contracts (the extension backbone)

> **Read this before subclassing anything.** These contracts are enforced by convention, not by abstract methods — breaking them silently produces wrong data.

### 4.1 `BaseScraper` ([core/scraper.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/scraper.py))
- Parent of every Playwright-driven scraper.
- Subclasses set: site config reference, `scraper_name` (used for `har/{scraper_name}/` lookup), URL keyword(s) for API interception, target cookie domain.
- Public surface: `fetch()` / `run()` orchestrates browser → intercept → parse → write HTML + data files.
- Do **not** override browser init or cookie inject without coordinating with §8.

### 4.2 `GameNewsBaseScraper` ([fetchers/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/base.py))
- News-specific base. ~L25–68: init from site config + incremental existing URLs + `ScraperConfig`. Declares subclass-overridable attributes: `game_key`, `site_config`, DOM fallback selectors.
- ~L100–143: unified `content_v2_user` response parser → list of dicts with keys `iInfoId, title, date, category, intro, poster_url, url`.
- Subclass contract: set `game_key` (must match a key in `config.json news_sites`); override DOM fallback selectors only if the site differs.

### 4.3 `GameNewsBaseExtractor` ([extractors/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/base.py))
- Defines `NewsItem` (~L20–30): `iInfoId, title, date, category, intro, poster_url, url, index`.
- ~L75–124: loads existing data; **backward-compatible with both 7-field (new) and 4-field (old) formats**; `get_existing_urls()` for dedup.
- `extract_news()` (~L128–168): main entry — parses HTML, merges incremental, dedups, sorts, returns `list[NewsItem]`.
- Subclass contract: set `game_key`; provide DOM fallback parse for the site's news container if it differs from Genshin's.

### 4.4 `NewsItem` (7-field canonical format)
| Field | Meaning |
| --- | --- |
| `iInfoId` | Server-side news ID (primary key in SQLite) |
| `title` | `sTitle` from API |
| `date` | Parsed from `dtStartTime` |
| `category` | `sCategoryName` |
| `intro` | `sIntro` |
| `poster_url` | Resolved from `poster_ext_key` lookup |
| `url` | Detail page URL built from `detail_url_pattern` |

> The 4-field legacy format (`title, date, link, ext`) is auto-detected on load but **never written** by current code. Treat it as read-only compatibility.

### 4.5 GUI base — `news_page.py` ([gui/pages/news_page.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_page.py))
- ~L10–68: renders title + 4 buttons (full fetch / incremental fetch / full extract / incremental extract).
- `_get_func()` is the abstract hook: subclass returns the specific `fetchers.run_*` / `extractors.run_*` callables.
- Subclass contract (~L5–15 of `news_genshin.py`): set `game_key`, bind functions in `_get_func()`. Do not duplicate button-rendering logic.

---

## 5. Data Flow

### 5.1 Fetch flow (Playwright interactive path)
```
run_news_<game>(incremental=...)      [fetchers/__init__.py]
  └─ <Game>NewsScraper                [fetchers/news/<game>.py]
       └─ GameNewsBaseScraper.run()   [fetchers/news/base.py]
            ├─ BaseScraper: launch Chromium, inject Firefox cookies
            ├─ page.on('response') intercept → match api_base_url keyword
            ├─ incremental: stop when existing URL seen
            └─ fallback: har/<scraper_name>/*.har   [utils/har_loader.py]
       → writes data/html/<lang_subdir>/<html_filename>
       → writes data/results/<data_filename>   (7-field lines)
```

### 5.2 Fetch flow (API direct, non-interactive)
```
_run_cli(args)                        [main.py]
  └─ MiHoYoApiClient(game, incremental, existing_urls).fetch_all()  [core/api_client.py]
       ├─ httpx GET content_v2_user (paginated)
       ├─ incremental: stop on existing URL
       └─ NewsStorage.upsert_items(game, items)  → SQLite
```
> This path **does not** start a browser and **does not** call `fetchers/`. Keep that separation — it's how Docker/CI run without Playwright.

### 5.3 Extract flow
```
run_extract_news_<game>(incremental=...)  [extractors/__init__.py]
  └─ <Game>NewsExtractor.extract_news()   [extractors/news/<game>.py + base.py]
       ├─ parse HTML container → NewsItem list
       ├─ load existing (7- or 4-field) for dedup
       ├─ incremental: merge + dedup by iInfoId/url
       └─ sort by date desc, write data/results/<data_filename>
```

### 5.4 Storage & export flow
```
SQLite (core/storage.py) ← upsert_items  (from fetch or extract)
                         → count_all     (--count, GUI)
                         → run_export_excel  (D: 1 sheet per game)
                         → generate_rss_feed / generate_json_feed
```

---

## 6. Configuration Reference

File: [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json)

### 6.1 Top-level fields

| Key | Type | Default | Effect |
| --- | --- | --- | --- |
| `user_url` | str | miyoushe user postList URL | Target for CLI 1–4 |
| `baike_url` | str | baike channel URL | Target for CLI 21 (character baike) |
| `weibo_url` | str | weibo u/ URL | Target for CLI 26–29 |
| `headless` | bool | `false` | Playwright headless toggle (debugging → `false`) |
| `wait_seconds` | int | `3` | Post-load wait before scroll/parse |
| `timeout` | int (ms) | `120000` | Per-navigation timeout |
| `user_agent` | str | Chrome 128 string | UA override |
| `project_root` | str | absolute path | Used to resolve data/har dirs |
| `output_dirs` | obj | `{html, images, data}` | Sub-paths under `data/` for each kind |
| `filenames` | obj | various | Filenames for user/baike/posts/weibo outputs |
| `news_sites` | obj | 4 entries | Per-site config (see §6.2) |
| `migration` | obj | `{enabled, genshin_old_filenames}` | Auto-migrate pre-V5 filenames |
| `browser_args` | list[str] | `--no-sandbox` etc. | Chromium launch args |
| `scroll_settings` | obj | `{delay, max_scroll_attempts}` | DOM-scroll fallback tuning |
| `retry_settings` | obj | `{max_attempts, delay}` | Retry policy for network/intercept |
| `incremental_settings` | obj | `{enabled, stop_on_existing, merge_data}` | Incremental behavior |
| `backup_settings` | obj | `{enabled, max_backups, backup_dir}` | Backup rotation |
| `weibo_settings.use_firefox_cookies` | bool | `true` | Inject Firefox cookies for weibo |
| `miyoushe_settings.use_firefox_cookies` | bool | `true` | Inject Firefox cookies for miyoushe |

### 6.2 `news_sites.<game_key>` fields

| Key | Required | Example | Effect |
| --- | --- | --- | --- |
| `url` | yes | `https://ys.mihoyo.com/main/news` | News index page (Playwright target) |
| `html_filename` | yes | `news_genshin.html` | Saved HTML filename |
| `data_filename` | yes | `news_genshin.txt` | Saved 7-field data filename |
| `scraper_name` | yes | `news_genshin` | Maps to `har/<scraper_name>/` fallback dir |
| `detail_url_pattern` | yes | `/main/news/detail/{iInfoId}` | Builds `url` field of NewsItem |
| `api_base_url` | yes | `.../content_v2_user/.../getContentList` | The intercepted/direct API endpoint |
| `api_chan_id` | yes | `719` | `iChanId` param |
| `api_app_id` | EN only | `32` | `iAppId` param (Genshin EN uses this) |
| `api_page_param` | yes | `iPage` | Page index query key |
| `api_page_size_param` | yes | `iPageSize` | Page size query key |
| `api_page_size` | yes | `5` or `9` | Page size value |
| `api_lang_param` | yes | `sLangKey` | Language query key |
| `api_lang_value` | yes | `zh-cn` / `en-us` | Language value |
| `fields` | yes | `["iInfoId", "sTitle", ...]` | Fields pulled from API response |
| `date_field` | yes | `dtStartTime` | Source field for `date` |
| `poster_ext_key` | yes | `720_1` / `banner` / `news-banner` | Key for poster URL lookup |
| `dir_key` | optional | `genshin` | Overrides output dir grouping (EN shares `genshin` dir) |
| `lang_subdir` | optional | `zh-cn` / `en-us` | Subdir under `data/html/` |
| `total` | optional | `4637` | Expected total (advisory; drives max-page) |

> Adding a new site = adding a new entry here + 3 subclass files. See §10.

---

## 7. Data File Layout

```
data/
├── html/
│   ├── genshin/zh-cn/news_genshin.html        # Playwright-saved page
│   ├── genshin/en-us/news_genshin_en.html
│   ├── news_zzz.html
│   └── news_starrail.html
├── results/
│   ├── news_genshin.txt          # 7-field lines (one NewsItem per line)
│   ├── news_genshin_en.txt
│   ├── news_zzz.txt
│   ├── news_starrail.txt
│   ├── posts.txt                 # miyoushe user posts
│   ├── weibo.txt
│   ├── image_urls.txt
│   ├── character_list.html
│   └── filtered/                 # TxtFilter output (CLI 39 / GUI "TXT 过滤")
│       └── <base>_<keyword>.txt   # filtered + date-desc sorted + renumbered
├── images/                       # Downloaded image assets
├── backups/                     # backup_manager rotation root
│   ├── posts.txt/<base_timestamp.ext>
│   └── news_genshin.txt/<base_timestamp.ext>
└── news.db                      # SQLite (NewsStorage); one table per game

har/                              # HAR fallback (auto-created on first use)
└── <scraper_name>/               # e.g. news_genshin/
    └── *.har / *.txt

logs/                             # logger output (auto-created)
output/                           # Excel/feed exports
├── news.xlsx
├── news_feed.xml
└── news_feed.json
```

- **7-field line format** in `*.txt`: pipe-delimited, order = `iInfoId | title | date | category | intro | poster_url | url`. (Old 4-field `title | date | link | ext` is tolerated on read only.)
- **SQLite** (`data/news.db`) uses one table per game key (`genshin`, `genshin_en`, `zzz`, `starrail`). Schema mirrors NewsItem.
- **Backups**: under `backup_dir` (default `data/backups`), one subdir per source filename, each holding timestamped copies. `max_backups` (default 10) trims oldest.

---

## 8. Cookie & HAR Fallback Mechanism

### 8.1 Firefox cookie injection
- Code: [utils/cookie_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/cookie_loader.py) (~L29–140).
- Profile discovery (~L29–58): walks Firefox profiles dir, prefers `default-release`/`default`, falls back to any profile containing `cookies.sqlite`.
- `load_firefox_cookies()` (~L58–140): opens `cookies.sqlite`, filters by target domain, converts `moz_cookies` rows → Playwright cookie dicts `{name, value, domain, path, secure, httpOnly, sameSite}`.
- Triggered by `BaseScraper` browser init (~L52–84) when `weibo_settings.use_firefox_cookies` / `miyoushe_settings.use_firefox_cookies` is `true`.
- Requirement: user must be logged into miyoushe / weibo in Firefox beforehand.

### 8.2 HAR fallback
- Code: [utils/har_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/har_loader.py).
- `har/{scraper_name}/` is scanned for `.har` / `.txt` files (~L16–48).
- `parse_har()` (~L51–96): extracts GET requests with JSON/text responses, dedups URLs, returns `{url, method, params, headers}`.
- **Trigger condition**: API interception fails (no matching response observed) within `timeout`. The scraper prints step-by-step guidance to export a HAR, expects the file at `har/<scraper_name>/`, and re-run picks it up.
- The `har/` tree is created on first use; do not commit HAR files (they contain session data).

---

## 9. CLI Modes

| Mode | Command | Path | Requires Playwright |
| --- | --- | --- | --- |
| Interactive CLI | `python main.py` | `MiHoYoToolKit.run()` loop | Yes (browser scrapers) |
| GUI | `python main.py --gui` | `gui.launch_gui()` | Yes |
| API direct fetch | `python main.py --fetch {genshin\|genshin_en\|zzz\|starrail\|all}` | `_run_cli()` → `core.api_client` | **No** |
| Export Excel | `python main.py --export-excel` | `_run_cli()` → `extractors.run_export_excel` | No |
| Show counts | `python main.py --count` | `_run_cli()` → `NewsStorage.count_all()` | No |

- Interactive handlers in [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) are decorated with `@log_function_call` + `@handle_errors` (see [utils/error_handler.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/error_handler.py) and [utils/logger.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/logger.py)). Preserve these decorators on any new handler.
- Menu items are registered in `MiHoYoToolKit._setup_options()` as `{str_number: {label, description, group, handler}}`. The CLI loop keys off the string index. Adding a CLI feature = add an entry here + a `_handler` method.

---

## 10. Extension Cookbook — Add a new news site (e.g. `honkai`)

> Follow in order. Every step has a clickable reference; mimic the existing `genshin`/`starrail` files exactly.

### Step 1 — Add config entry
Edit [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json): add a new key under `news_sites` with all fields from §6.2. Set `scraper_name` to `news_honkai` (controls `har/news_honkai/` fallback dir).

### Step 2 — Fetcher subclass
Create [fetchers/news/honkai.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/honkai.py) modeled on [fetchers/news/genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/genshin.py):
- `class HonkaiNewsScraper(GameNewsBaseScraper)` with `game_key = "honkai"`.
- Override DOM fallback selectors only if the Honkai news container differs.

### Step 3 — Export fetcher entry point
Edit [fetchers/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/__init__.py): export `HonkaiNewsScraper` and a `run_news_honkai(incremental=False)` function, mirroring the existing `run_news_genshin`.

### Step 4 — Extractor subclass
Create [extractors/news/honkai.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/honkai.py) modeled on [extractors/news/genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/genshin.py): `class HonkaiNewsExtractor(GameNewsBaseExtractor)` with `game_key = "honkai"`.

### Step 5 — Export extractor entry point
Edit [extractors/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/__init__.py): export `HonkaiNewsExtractor` and `run_extract_news_honkai(incremental=False)`.

### Step 6 — Storage table
`NewsStorage` auto-creates a table per `game_key`, so no schema change is needed. Verify by running `python main.py --count` after a fetch.

### Step 7 — GUI page
Create [gui/pages/news_honkai.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_honkai.py) modeled on [gui/pages/news_genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_genshin.py): subclass `news_page`'s base, set `game_key="honkai"`, return the new `run_*` functions from `_get_func()`. Register the page in [gui/pages/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/__init__.py) and add it to the sidebar in [gui/main_window.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/main_window.py).

### Step 8 — CLI menu items
In [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) `_setup_options()`, add 4 entries (fetch / incremental fetch / extract / incremental extract) continuing the numbering sequence (currently ends at 20 for Star Rail news). Add 4 `@log_function_call @handle_errors` handler methods that lazy-import the new `run_*` functions and call them with `incremental=`.

### Step 9 — Non-interactive path (optional but recommended)
Extend `--fetch` choices in `argparse` and the `games` list in `_run_cli()` to include `honkai`. `core.api_client.MiHoYoApiClient` already keys off `game_key`, so only the config entry is needed.

### Step 10 — Tests
Add [tests/test_news.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_news.py) cases for the new scraper/extractor; add a fixture HAR under `tests/` if you need offline parse tests (see [tests/test_har_fixture.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_har_fixture.py) for the pattern).

### Step 11 — Update version + docs
Bump version in `main.py` `MiHoYoToolKit.__init__` and in the human [README.md](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/README.md) badges. Add an entry to [CHANGELOG.md](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/CHANGELOG.md). Add a row to the news coverage table.

---

## 11. Testing

### 11.1 Run commands
```bash
python -m unittest tests.test_news -v          # news fetcher/extractor
python -m unittest tests.test_storage -v      # SQLite NewsStorage
python -m unittest tests.test_api_client -v   # MiHoYoApiClient
python -m unittest tests.test_extractors -v   # extractor edge cases
python -m unittest tests.test_excel_writer -v # Excel export
python -m unittest tests.test_feed -v         # RSS/JSON feed
python -m unittest tests.test_models -v       # pydantic models
python -m unittest tests.test_cli -v         # CLI argparse / _run_cli
python -m unittest tests.test_har_fixture -v  # HAR parsing fixture
python -m unittest tests.test_txt_filter -v   # TXT filter / sort / renumber
python -m unittest discover -s tests -v       # everything
python tests/integration_test.py              # end-to-end script (not a unittest)
```

### 11.2 Test inventory

| File | Covers |
| --- | --- |
| [tests/test_news.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_news.py) | `GameNewsBaseScraper` / `GameNewsBaseExtractor` parsing & merge |
| [tests/test_storage.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_storage.py) | `NewsStorage` upsert / dedup / count |
| [tests/test_api_client.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_api_client.py) | `MiHoYoApiClient.fetch_all` pagination & incremental stop |
| [tests/test_extractors.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_extractors.py) | NewsItem 7-field vs 4-field compat, edge cases |
| [tests/test_excel_writer.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_excel_writer.py) | Excel multi-sheet export |
| [tests/test_feed.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_feed.py) | RSS 2.0 + JSON Feed generation |
| [tests/test_models.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_models.py) | pydantic model validation |
| [tests/test_cli.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_cli.py) | argparse, `--fetch`, `--export-excel`, `--count` |
| [tests/test_har_fixture.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_har_fixture.py) | HAR parsing against a fixture file |
| [tests/test_txt_filter.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_txt_filter.py) | `TxtFilter` line parsing, keyword OR matching (case-insensitive), multi-file merge, date-desc sort, renumber |
| [tests/integration_test.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/integration_test.py) | Manual end-to-end (not part of unittest discovery) |

### 11.3 Conventions
- Framework: stdlib `unittest`. No pytest dependency — keep it that way unless explicitly asked.
- New tests: `tests/test_<module>.py`, class `Test<Subject>(unittest.TestCase)`.
- Use fixtures (sample HTML/HAR) under `tests/` rather than hitting the live API in unit tests.
- `integration_test.py` is intentionally not in the unittest suite — do not `import` it from `__init__.py`.

---

## 12. Debugging Guide

### 12.1 Failure-mode → where to look

| Symptom | First place to look |
| --- | --- |
| Browser opens but no API intercepted | `core/scraper.py` ~L84–161; verify `api_base_url` keyword in site config; check `headless: false` to watch |
| "Playwright dependency missing" at startup | [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) `main()` — interactive path requires `playwright install chromium` |
| Cookie login not working (still asked to log in) | [utils/cookie_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/cookie_loader.py); confirm Firefox profile path; confirm `*_settings.use_firefox_cookies=true`; confirm user is logged in inside Firefox |
| Incremental fetch overwrites instead of merging | `incremental_settings.{enabled, stop_on_existing, merge_data}` in [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json); also `extractors/news/base.py` ~L75–124 loader |
| Backup rotation deletes wanted files | [utils/backup_manager.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/backup_manager.py) ~L93–111; raise `backup_settings.max_backups` |
| SQLite "no such table" | `core/storage.py` ~L35–63; table is created on first `upsert_items` for that `game_key` — run a fetch first |
| `--fetch` returns 0 items | `core/api_client.py` `fetch_all` ~L171–241; check `api_chan_id` / `api_app_id` (EN only) in config |
| GUI button does nothing | [gui/pages/news_<game>.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages) `_get_func()` returns the wrong callable; check [gui/workers.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/workers.py) QThread wiring |
| Migration prompt every launch | `migration.enabled=true` + leftover old filenames; either finish migration or set `migration.enabled=false` |

### 12.2 HAR fallback workflow (when API interception fails)
1. Run the failing fetch with `headless: false`.
2. Watch the console; the scraper prints exact steps to export a HAR from DevTools.
3. Save the HAR as `har/<scraper_name>/<any-name>.har` (or `.txt` with raw JSON).
4. Re-run the same fetch; `utils/har_loader.py` will pick it up automatically.
5. HAR files contain session data → do **not** commit them (they're gitignored).

### 12.3 Logs
- Logger: [utils/logger.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/logger.py) `setup_logger("miHoYo_ToolKit")`.
- Handlers are wrapped with `@log_function_call` (entry/exit) and `@handle_errors` (catches + logs + continues). Inspect `logs/` and the in-app bottom log panel (GUI).

---

## 13. Common Pitfalls / Known Issues

1. **`iChanId` / `api_app_id` drift**: HoYo occasionally changes channel IDs. If a site that worked returns 0 items, suspect the API params in [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json). Verify against the live site's DevTools network tab before "fixing" the code.
2. **Firefox cookie profile selection**: On machines with multiple Firefox installs/profiles, [utils/cookie_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/cookie_loader.py) picks `default-release` first; if the user is logged in under a different profile, cookies silently won't be found. No error is raised — the page just asks for login.
3. **4-field vs 7-field data merge**: [extractors/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/base.py) ~L75–124 auto-detects legacy 4-field files on load. **Never** write 4-field output from new code — it loses `iInfoId` and breaks SQLite dedup.
4. **Backup naming collisions**: `backup_manager` names files `<base>_<timestamp>.<ext>`. Two backups within the same second collide. If you script bulk operations, add a sleep or a custom backup name.
5. **`headless: false` is the default**: [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json) ships `headless: false` for debugging. CI/Docker should override to `true` or use the `--fetch` path that ignores this flag.
6. **Font loading in GUI**: [gui/fonts.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/fonts.py) `load_game_fonts()` loads game fonts into QFontDatabase at startup but does **not** auto-apply them — the GUI uses the platform-native system font by default. The returned `{key: family}` dict is reserved for a future settings page; `apply_app_font()` is the reserved hook to switch the global font. A missing font file falls back silently to the system font.
7. **`--fetch` bypasses `fetchers/`**: Any logic added to a Playwright scraper will **not** run in API-direct mode. Mirror critical changes in [core/api_client.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/api_client.py) if the change must apply to both paths.
8. **Migration runs on every interactive launch**: `check_and_migrate()` in [utils/migration.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/migration.py) is called from `main()`. If old files keep reappearing (e.g., restored from a backup), the prompt recurs.
9. **`total` is advisory, not enforced**: `api_client.fetch_all` uses `total` to bound pagination but also enforces a max-page safety cap. A wrong `total` slows scraping but doesn't break it; a missing `total` triggers a second probe request.
10. **`project_root` in config is absolute**: [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json) hardcodes `D:\...`. Moving the repo to another path without updating this breaks `data/` resolution. Prefer editing `config_manager` to derive from `__file__` rather than baking in another absolute path.

---

## 14. Pre-flight Checklist (before modifying X, read Y)

Before touching any module, read its base class + tests first.

| If you plan to modify… | You MUST first read… |
| --- | --- |
| A news scraper (any `fetchers/news/*.py`) | [fetchers/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/base.py) + [core/scraper.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/scraper.py) + [tests/test_news.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_news.py) |
| A news extractor (any `extractors/news/*.py`) | [extractors/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/base.py) + [tests/test_extractors.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_extractors.py) |
| `core/storage.py` | [tests/test_storage.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_storage.py) + §4.4 (NewsItem 7-field contract) |
| `core/api_client.py` | [tests/test_api_client.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_api_client.py) + §5.2 (API-direct path) |
| `config.json` schema | §6 (this doc) + [core/config_manager.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/config_manager.py) |
| `utils/cookie_loader.py` or `utils/har_loader.py` | §8 + the matching test file |
| `gui/pages/*.py` | [gui/pages/news_page.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_page.py) (base) + [gui/workers.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/workers.py) |
| `main.py` CLI handlers | §9 + the `@log_function_call @handle_errors` decorator pair on every existing handler |
| Export/feed | [tests/test_excel_writer.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_excel_writer.py) + [tests/test_feed.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_feed.py) |

---

## 15. AI Agent Hard Constraints (Do / Don't)

### DO
- **DO** keep the 7-field `NewsItem` shape (`iInfoId, title, date, category, intro, poster_url, url`) across fetcher → extractor → storage → export. It is the integration contract.
- **DO** add new sites by subclassing the existing bases (§10) — never copy-paste a whole scraper.
- **DO** preserve the `@log_function_call` + `@handle_errors` decorator stack on every `MiHoYoToolKit` handler method in [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py).
- **DO** lazy-import fetchers/extractors inside handlers (the existing pattern) so the interactive CLI starts fast and so `--fetch` can run without Playwright installed.
- **DO** keep `fetchers/` (Playwright path) and `core/api_client.py` (API-direct path) in sync when changing parsing logic — they are intentionally separate but must agree on output shape.
- **DO** run the relevant `tests/test_*.py` after touching the matching module.
- **DO** use dot-path config keys via `config_manager.get("news_sites.<game>.<field>")` rather than reading [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json) directly.
- **DO** write new tests as `unittest.TestCase` classes in `tests/test_<module>.py`.
- **DO** update this document (and bump version per §16) whenever a base class contract, config field, or data format changes.

### DON'T
- **DON'T** change the `config.json` schema without updating §6 of this doc and [core/config_manager.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/config_manager.py); many sites' scrapers read keys by name.
- **DON'T** bypass the Firefox cookie injection in `BaseScraper` to "just log in manually" — that breaks unattended runs and the `--fetch` Docker path expects cookies to be present.
- **DON'T** break the incremental-merge logic in [extractors/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/base.py) ~L75–124 (the 7-field/4-field compatibility). Users have years of legacy data files.
- **DON'T** write 4-field data files. The legacy format is read-only.
- **DON'T** make `core/api_client.py` depend on Playwright, `fetchers/`, or a TTY — it is the container/CI path and must stay headless-friendly.
- **DON'T** reorder or rename the `news_sites` keys (`genshin`, `genshin_en`, `zzz`, `starrail`) — they are also SQLite table names; renaming loses data.
- **DON'T** add new CLI menu numbers that collide with existing ones (1–39 assigned); `main.py` `_setup_options` keys are strings and the loop sorts numerically. New features take ≥40.
- **DON'T** commit HAR files under `har/` — they contain session cookies. The directory is gitignored; keep it that way.
- **DON'T** touch [resources/font/](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/resources/font) — third-party HoYo-Glyphs assets, unmodified, non-commercial. See `resources/font/LICENSE`.
- **DON'T** introduce pytest or any runner other than stdlib `unittest` without explicit user approval.
- **DON'T** remove the `@log_function_call` / `@handle_errors` decorators "to clean up" — they are the CLI's error containment boundary.
- **DON'T** bake new absolute paths into [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json); derive paths from `config_manager.get_output_dir(...)` or `__file__` instead.

---

## 16. Version & Compatibility Policy

### 16.1 Current
- **Version**: 1.0.1 (held in [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py) `MiHoYoToolKit.__init__` and the human README badge).
- **Python**: 3.8+ (use no syntax that requires 3.9+ without bumping the floor).

### 16.2 Breaking-change history (highlights)
- **V1.0.0** — First stable release. Version number reset from 5.0.0 to 1.0.0. GUI switched to PySide6 native style (no custom QSS). Added TXT filter with preview, fuzzy/exact match modes, tqdm progress bars. Fixed weibo `mblogid` parsing, full pagination (no artificial limits), English date parsing. Added `CHANGELOG.md`.
- **V5.0.0** — News storage moved to SQLite (`data/news.db`); data files retained for human reading. Auto-migration of pre-V5 filenames via `utils/migration.py`. 7-field `NewsItem` introduced; 4-field legacy read-only.
- **V5.x non-interactive path** — Added `--fetch` / `--export-excel` / `--count` + `core/api_client.py` for container use without Playwright.
- **Pre-V5** — Flat `data/` layout, single news file per site, no SQLite, no GUI.

### 16.3 Backward-compatibility commitments
- **Data files**: 4-field legacy `*.txt` will keep loading; never write that format.
- **Config**: existing top-level keys are stable; new keys are additive. Removing a key requires a major version bump.
- **SQLite schema**: table-per-game is stable; column additions must be nullable/defaulted so older binaries can still read.
- **CLI menu numbers**: existing 1–39 stay assigned to their current features; new features take ≥40.

### 16.4 Bumping
- Patch: bug fixes, no schema/config/CLI-number changes.
- Minor: additive features (new site, new export format) — update §10/§6, no removals.
- Major: any of — `NewsItem` shape change, `config.json` schema break, CLI menu renumbering, SQLite schema break.

---

## 17. Build & Packaging

### 17.1 Build scripts

| Platform | Script | Commands |
| --- | --- | --- |
| Windows | [build.ps1](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.ps1) / [build.bat](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.bat) | `deps`, `test`, `exe`, `exe-onefile`, `exe-onedir`, `docker`, `clean`, `all` |
| Linux/macOS | [build.sh](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.sh) | `deps`, `test`, `docker`, `clean`, `all` |

### 17.2 EXE packaging (Windows)

Uses [PyInstaller](https://pyinstaller.org/) with [app.spec](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/app.spec).

- **Icon**: [resources/icon/app.ico](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/resources/icon/app.ico)
- **Version metadata**: [version_info.txt](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/version_info.txt)
- **Modes**: `onefile` (single EXE) or `onedir` (directory) — set `PYI_MODE` env var
- **Playwright browser**: bundled from local `browser/` dir (`PLAYWRIGHT_BROWSERS_PATH`)

```powershell
# One-file EXE (default)
.\build.ps1 exe-onefile

# Directory mode
.\build.ps1 exe-onedir
```

### 17.3 Docker

[Dockerfile](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/Dockerfile) supports two build modes via `--build-arg MODE`:

- `MODE=cli` (default): lightweight, API/CLI only, no Playwright/PySide6
- `MODE=full`: full mode with Playwright + PySide6 + Chromium + X11 libs

```bash
docker build -t mihoyo-toolkit .
docker build --build-arg MODE=full -t mihoyo-toolkit:full .
```

### 17.4 Cleanup

Both CLI menu (option 40) and build script (`clean`) remove `__pycache__/`, `*.pyc`, `logs/*.log`, `build/`, `dist/`, `.pytest_cache/`. All require typing `YES` to confirm. Skips `.venv/`, `.git/`, `browser/`, `data/`, `logs/`, `har/`.

### 17.5 CI/CD

[.github/workflows/build.yml](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/.github/workflows/build.yml) runs:
- **test** job: unit tests on Python 3.8–3.11 (every push/PR)
- **build-windows** job: PyInstaller EXE (release only)
- **build-docker** job: Docker image (release only)

---

## 18. File Index (clickable)

### Entry & config
- [main.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/main.py)
- [config.json](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/config.json)
- [requirements.txt](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/requirements.txt)
- [CHANGELOG.md](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/CHANGELOG.md)

### Build & packaging
- [app.spec](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/app.spec) — PyInstaller spec
- [version_info.txt](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/version_info.txt) — EXE version metadata
- [build.ps1](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.ps1) — Windows build script
- [build.bat](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.bat) — Windows batch wrapper
- [build.sh](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/build.sh) — Linux/macOS build script
- [Dockerfile](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/Dockerfile) — Docker build (cli/full modes)
- [.github/workflows/build.yml](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/.github/workflows/build.yml) — CI/CD

### core/
- [core/scraper.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/scraper.py) — `BaseScraper`
- [core/api_client.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/api_client.py) — `MiHoYoApiClient`
- [core/storage.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/storage.py) — `NewsStorage`
- [core/feed.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/feed.py) — RSS/JSON Feed
- [core/config_manager.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/config_manager.py) — `config_manager`
- [core/models.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/core/models.py) — pydantic models

### fetchers/
- [fetchers/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/__init__.py)
- [fetchers/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/base.py) — `GameNewsBaseScraper`
- [fetchers/news/genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/genshin.py)
- [fetchers/news/genshin_en.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/genshin_en.py)
- [fetchers/news/zzz.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/zzz.py)
- [fetchers/news/starrail.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/news/starrail.py)
- [fetchers/user.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/user.py)
- [fetchers/weibo.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/weibo.py)
- [fetchers/baike.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/baike.py)
- [fetchers/tutorial.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/tutorial.py)
- [fetchers/custom.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/fetchers/custom.py)

### extractors/
- [extractors/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/__init__.py)
- [extractors/news/base.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/base.py) — `GameNewsBaseExtractor`, `NewsItem`
- [extractors/news/genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/genshin.py)
- [extractors/news/genshin_en.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/genshin_en.py)
- [extractors/news/zzz.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/zzz.py)
- [extractors/news/starrail.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/news/starrail.py)
- [extractors/weibo.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/weibo.py)
- [extractors/images.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/images.py)
- [extractors/tutorial.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/tutorial.py)
- [extractors/excel_writer.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/excel_writer.py)
- [extractors/txt_filter.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/extractors/txt_filter.py) — `TxtFilter`, `run_filter`, `preview`, `write_to_file`

### gui/
- [gui/__init__.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/__init__.py) — `launch_gui()`
- [gui/paths.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/paths.py) — `get_app_icon_path()`
- [gui/main_window.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/main_window.py)
- [gui/fonts.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/fonts.py) — game font loader (reserved for settings page)
- [gui/workers.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/workers.py)
- [gui/widgets.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/widgets.py)
- [gui/pages/news_page.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_page.py) — base
- [gui/pages/news_genshin.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_genshin.py)
- [gui/pages/news_genshin_en.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_genshin_en.py)
- [gui/pages/news_zzz.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_zzz.py)
- [gui/pages/news_starrail.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/news_starrail.py)
- [gui/pages/user_posts.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/user_posts.py)
- [gui/pages/other.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/other.py)
- [gui/pages/weibo.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/weibo.py)
- [gui/pages/filter.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/filter.py) — TXT filter page (preview + direct run)
- [gui/pages/preview_dialog.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/preview_dialog.py) — `PreviewDialog` (QTableWidget, confirm/modify/cancel)
- [gui/pages/system.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/gui/pages/system.py)

### utils/
- [utils/cookie_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/cookie_loader.py)
- [utils/har_loader.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/har_loader.py)
- [utils/backup_manager.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/backup_manager.py)
- [utils/error_handler.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/error_handler.py)
- [utils/migration.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/migration.py)
- [utils/logger.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/utils/logger.py)

### tests/
- [tests/test_news.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_news.py)
- [tests/test_storage.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_storage.py)
- [tests/test_api_client.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_api_client.py)
- [tests/test_extractors.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_extractors.py)
- [tests/test_excel_writer.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_excel_writer.py)
- [tests/test_feed.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_feed.py)
- [tests/test_models.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_models.py)
- [tests/test_cli.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_cli.py)
- [tests/test_har_fixture.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_har_fixture.py)
- [tests/test_txt_filter.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/test_txt_filter.py)
- [tests/integration_test.py](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/tests/integration_test.py)

---

*End of AI Agent Reference. For human-facing overview, see [README.md](file:///D:/LingLan/material/github/vers123/mihoyo/mihoyo-tool-kit/README.md).*
