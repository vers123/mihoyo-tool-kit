"""
新闻抓取公共基类
基于 content_v2_user 统一 API 架构（原神/绝区零/星穹铁道通用）

抓取策略：API 直接循环请求 + 浏览器验证模式
1. 启动浏览器访问页面，验证 API 可访问性
2. 基于 iTotal 和 page_size 计算总页数
3. 直接循环发起 API 请求获取全部数据
4. 用全部数据构建完整 HTML
5. 保留 API 拦截 + DOM 回退作为兜底机制
"""

import time
import json
import html
import math
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser
from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry
from utils.har_loader import find_har_file, load_api_pattern_from_har, print_har_instructions


class GameNewsBaseScraper(BaseScraper):
    """游戏新闻抓取器基类 - 基于 content_v2_user 统一 API 架构

    子类需要覆盖的属性/方法：
    - game_key: 游戏标识（genshin/zzz/starrail）
    - site_config: 从 config 中获取的站点配置
    - dom_item_selector: DOM 回退时的列表项选择器
    - load_more_selector: "加载更多"按钮选择器（兜底用）
    """

    # 子类必须设置
    game_key: str = ""

    def __init__(self, incremental: bool = False):
        # 获取站点配置
        self.site_config = config_manager.get_news_config(self.game_key)
        if not self.site_config:
            raise ValueError(f"未找到游戏 '{self.game_key}' 的新闻配置")

        # 增量模式：加载已有数据
        existing_urls = None
        if incremental and config_manager.get("incremental_settings.enabled", True):
            existing_urls = self._get_existing_urls()
            if existing_urls:
                print(f"[INFO] 增量模式: 已存在 {len(existing_urls)} 条数据")

        # 构建 ScraperConfig
        scraper_config = ScraperConfig(
            url=self.site_config["url"],
            output_filename=self.site_config["html_filename"],
            headless=config_manager.get("headless", False),
            wait_seconds=config_manager.get("wait_seconds", 3),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0),
            incremental_mode=incremental,
            existing_urls=existing_urls,
            scraper_name=self.site_config["scraper_name"],
            api_url_keywords=["getContentList", "content_v2_user"],
            api_domain_filter="mihoyo.com",
            use_firefox_cookies=False,
        )
        super().__init__(scraper_config)

        # 输出路径（按游戏分子目录）
        self.html_dir = config_manager.get_news_output_dir(self.game_key, "html")
        self.save_path = config_manager.get_news_scraper_config(self.game_key)["output_path"]

        # DOM 回退选择器（子类可覆盖）
        self.dom_item_selector = 'li[class*="news"][class*="item"]'
        self.load_more_selector = 'li[class*="more"], button[class*="more"]'

    def _get_existing_urls(self) -> set:
        """获取已存在的 URL 集合（供增量模式使用）

        子类可以覆盖此方法以使用对应的 extractor。
        默认使用基类提取逻辑从数据文件读取。
        """
        # 默认从 data 文件解析
        data_dir = config_manager.get_news_output_dir(self.game_key, "data")
        data_path = data_dir / self.site_config["data_filename"]
        import os
        if not os.path.exists(data_path):
            return set()

        try:
            with open(data_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            urls = set(re.findall(r'\((https?://[^\)]+)\)', content))
            return urls
        except Exception:
            return set()

    def _extract_items_from_api(self, data: dict) -> list:
        """从 API 响应中提取新闻列表（统一 content_v2_user 格式）"""
        news_list = []

        if not isinstance(data, dict):
            return news_list

        # content_v2_user 标准结构: data.list
        list_data = data.get("data", {}).get("list", [])
        if not isinstance(list_data, list):
            return news_list

        for item in list_data:
            if not isinstance(item, dict):
                continue

            info_id = str(item.get("iInfoId", ""))
            title = item.get("sTitle", "")
            date_str = item.get(self.site_config.get("date_field", "dtStartTime"), "")
            category = item.get("sCategoryName", "")
            intro = item.get("sIntro", "")

            if not info_id or not title:
                continue

            # 构建详情页 URL
            detail_url_pattern = self.site_config["detail_url_pattern"]
            url_path = detail_url_pattern.format(iInfoId=info_id)
            full_url = self._make_full_url(url_path)

            # 提取封面图
            poster_url = self._extract_poster_url(item)

            news_list.append({
                "iInfoId": info_id,
                "sTitle": title,
                "date": str(date_str),
                "sCategoryName": category,
                "sIntro": intro,
                "poster_url": poster_url,
                "url": full_url,
            })

        return news_list

    def _extract_poster_url(self, item: dict) -> str:
        """从 sExt 中提取封面图 URL"""
        s_ext_str = item.get("sExt", "")
        if not s_ext_str:
            return ""

        try:
            s_ext = json.loads(s_ext_str)
        except (json.JSONDecodeError, TypeError):
            return ""

        poster_key = self.site_config.get("poster_ext_key", "")
        if not poster_key or poster_key not in s_ext:
            return ""

        poster_data = s_ext[poster_key]
        if isinstance(poster_data, list) and len(poster_data) > 0:
            return poster_data[0].get("url", "")
        elif isinstance(poster_data, dict):
            return poster_data.get("url", "")

        return ""

    def _make_full_url(self, path: str) -> str:
        """将路径拼接为完整 URL"""
        base_url = self.site_config["url"]
        if path.startswith("http"):
            return path
        # 从基础 URL 提取域名
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        return f"{parsed.scheme}://{parsed.netloc}{path}"

    def _build_html_from_api_data(self, items: list) -> str:
        """将 API 数据构建为完整 HTML

        统一的 HTML 结构，子类可覆盖以自定义样式。
        """
        game_label = self._get_game_label()
        html_parts = [
            f'<!DOCTYPE html><html lang="zh-cn"><head><meta charset="utf-8">',
            f'<title>{game_label}新闻</title></head><body>',
            f'<div class="news-container">',
            f'<h1>{game_label}新闻列表（共 {len(items)} 条）</h1>',
            '<ul class="news__list">'
        ]

        for item in items:
            info_id = item.get("iInfoId", "")
            title = item.get("sTitle", "")
            date = item.get("date", "")
            category = item.get("sCategoryName", "")
            intro = item.get("sIntro", "")
            poster_url = item.get("poster_url", "")
            url = item.get("url", "")

            # 获取相对路径用于 href
            from urllib.parse import urlparse
            parsed = urlparse(url)
            url_path = parsed.path
            if parsed.query:
                url_path += "?" + parsed.query

            safe_title = html.escape(title)
            safe_url = html.escape(url_path)
            safe_date = html.escape(date)
            safe_category = html.escape(category)
            safe_intro = html.escape(intro)
            safe_poster = html.escape(poster_url)

            # 构建新闻项 HTML
            item_html = f'<li class="news__item" data-id="{info_id}">'

            # 封面图
            if poster_url:
                item_html += f'<div class="news__poster"><img src="{safe_poster}" alt="{safe_title}"></div>'

            # 内容区
            item_html += '<div class="news__content">'

            # 分类标签
            if category:
                item_html += f'<span class="news__category">{safe_category}</span>'

            # 标题
            item_html += (
                f'<a href="{safe_url}" class="news__title">'
                f'<h3 title="{safe_title}">{safe_title}</h3>'
                f'</a>'
            )

            # 摘要
            if intro:
                item_html += f'<p class="news__intro">{safe_intro}</p>'

            # 日期
            item_html += f'<div class="news__date">{safe_date}</div>'

            item_html += '</div></li>'
            html_parts.append(item_html)

        html_parts.append('</ul></div></body></html>')
        return ''.join(html_parts)

    def _get_game_label(self) -> str:
        """获取游戏中文名标签（用于 HTML 标题）"""
        labels = {
            "genshin": "原神",
            "zzz": "绝区零",
            "starrail": "崩坏：星穹铁道",
        }
        return labels.get(self.game_key, self.game_key)

    def _fetch_all_via_api_direct(self) -> list:
        """直接通过 API 循环请求获取全部新闻数据

        这是首选策略，比浏览器滚动触发更快更稳定。
        """
        api_base_url = self.site_config["api_base_url"]
        chan_id = self.site_config["api_chan_id"]
        page_param = self.site_config["api_page_param"]
        page_size_param = self.site_config["api_page_size_param"]
        page_size = self.site_config["api_page_size"]
        lang_param = self.site_config.get("api_lang_param", "sLangKey")
        lang_value = self.site_config.get("api_lang_value", "zh-cn")

        # 先请求第一页获取 iTotal
        import urllib.request
        import urllib.parse

        def build_url(page: int) -> str:
            params = {
                page_param: page,
                page_size_param: page_size,
                "iChanId": chan_id,
                lang_param: lang_value,
            }
            return f"{api_base_url}?{urllib.parse.urlencode(params)}"

        all_items = []
        total = 0
        current_page = 1
        max_pages = 1000  # 安全上限

        print(f"[INFO] 开始 API 直接抓取（频道 {chan_id}，每页 {page_size} 条）")

        while current_page <= max_pages:
            try:
                url = build_url(current_page)
                req = urllib.request.Request(url, headers={
                    "User-Agent": config_manager.get("user_agent", ""),
                    "Accept": "application/json",
                    "Referer": self.site_config["url"],
                })

                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                items = self._extract_items_from_api(data)

                if not items:
                    print(f"[INFO] 第 {current_page} 页无数据，抓取结束")
                    break

                # 从第一页获取总数
                if current_page == 1:
                    total = data.get("data", {}).get("iTotal", 0)
                    total_pages = math.ceil(total / page_size) if total else 0
                    if total_pages > 0:
                        max_pages = min(max_pages, total_pages)
                    print(f"[INFO] 新闻总数: {total} 条，共 {max_pages} 页")

                all_items.extend(items)
                print(f"[INFO] 第 {current_page}/{max_pages} 页: +{len(items)} 条（累计 {len(all_items)} 条）")

                # 增量模式：检查是否遇到已存在数据
                if (self.config.incremental_mode and self.config.existing_urls
                        and config_manager.get("incremental_settings.stop_on_existing", True)):
                    found_existing = False
                    for item in items:
                        if item.get("url", "") in self.config.existing_urls:
                            print(f"[INFO] 增量模式：发现已存在数据，停止抓取")
                            found_existing = True
                            break
                    if found_existing:
                        break

                # 如果当前页条数少于 page_size，说明是最后一页
                if len(items) < page_size:
                    print("[INFO] 已到达最后一页")
                    break

                current_page += 1

            except Exception as e:
                print(f"[WARN] 第 {current_page} 页请求失败: {e}")
                break

        return all_items

    def _process_page(self, page: Page) -> str:
        """处理页面：优先 API 直接抓取，失败则回退到浏览器拦截 + DOM"""
        self._setup_api_interception(page)

        page.goto(self.config.url, timeout=self.config.timeout)
        page.wait_for_load_state("networkidle")
        time.sleep(self.config.wait_seconds)

        # 策略 1：API 直接循环请求（首选，最快最稳定）
        print("\n[INFO] 策略1：尝试 API 直接抓取...")
        api_items = self._fetch_all_via_api_direct()
        if api_items:
            print(f"\n[OK] API 直接抓取成功，共 {len(api_items)} 条新闻")
            return self._build_html_from_api_data(api_items)

        # 策略 2：浏览器 API 拦截 + 滚动
        print("\n[WARN] API 直接抓取失败，尝试策略2：浏览器拦截 + 滚动...")
        self._scroll_for_data(page)

        if self._api_data:
            print(f"\n[OK] API 拦截成功，共 {len(self._api_data)} 条新闻")
            return self._build_html_from_api_data(self._api_data)

        # 策略 3：检查 HAR 文件回退
        print("\n[WARN] 自动检测API未获取到数据")
        har_path = find_har_file(self.config.scraper_name)
        if har_path:
            print(f"[INFO] 检测到HAR文件: {har_path}")
            print("[INFO] 请删除HAR文件后重新运行，或手动检查API配置")
        else:
            print_har_instructions(
                self.config.scraper_name,
                self.config.url,
                ["api-takumi-static.mihoyo.com", "act-api-takumi-static.mihoyo.com"]
            )

        # 策略 4：回退到 DOM 抓取
        print("[INFO] 回退到DOM抓取模式...")
        return page.content()

    def _scroll_for_data(self, page: Page) -> None:
        """滚动页面触发 API 请求（兜底用）"""
        scroll_delay = self.config.scroll_delay
        last_height = page.evaluate("document.body.scrollHeight")
        attempts = 0
        max_attempts = 5

        while not self._api_stop_requested:
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(scroll_delay)

            # 尝试点击"加载更多"
            try:
                locator = page.locator(self.load_more_selector)
                if locator.count() > 0 and locator.first.is_visible():
                    locator.first.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            new_height = page.evaluate("document.body.scrollHeight")

            if self._api_stop_requested:
                break

            if new_height == last_height:
                attempts += 1
                if attempts >= max_attempts:
                    print("[INFO] 页面高度不再变化，停止滚动")
                    break
            else:
                attempts = 0

            last_height = new_height

    def _fetch_via_api_client(self) -> list:
        """使用 MiHoYoApiClient 直接请求 API（不启动浏览器）

        P 档主路径（O1+O2）：httpx 连接池 + tenacity 重试，
        失败返回空列表，由上层回退到浏览器路径。
        """
        try:
            from core.api_client import MiHoYoApiClient

            client = MiHoYoApiClient(
                self.game_key,
                incremental=self.config.incremental_mode,
                existing_urls=self.config.existing_urls,
            )
            return client.fetch_all()
        except Exception as e:
            print(f"[WARN] API 客户端异常: {e}")
            return []

    def run(self) -> str:
        """执行主抓取流程

        优先走 API 客户端（不启浏览器）；失败才回退到 Playwright 浏览器路径
        （API 拦截 + 滚动 + HAR + DOM）。
        """
        game_label = self._get_game_label()
        print(f"\n【启动】抓取{game_label}新闻: {self.config.url}")

        # 策略 0（首选）：API 客户端直连，不启动浏览器
        print("[INFO] 策略0：尝试 API 客户端直连...")
        api_items = self._fetch_via_api_client()
        if api_items:
            print(f"\n[OK] API 客户端抓取成功，共 {len(api_items)} 条新闻")
            html_content = self._build_html_from_api_data(api_items)
            self._save_html(html_content)
            return html_content

        # 策略 1+（回退）：浏览器路径（API 拦截 + 滚动 + HAR + DOM）
        print("\n[WARN] API 客户端未获取到数据，回退到浏览器路径...")
        with sync_playwright() as p:
            browser, page = self._setup_browser(p)
            try:
                html_content = self._process_page(page)
            finally:
                browser.close()

        self._save_html(html_content)
        return html_content

    def _save_html(self, html_content: str) -> None:
        """保存 HTML 内容到文件（按游戏分子目录）"""
        import os
        os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
        with open(self.save_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ 完成：{self.save_path}")
