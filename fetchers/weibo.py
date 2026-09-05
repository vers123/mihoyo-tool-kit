import re
import time
import html
import json
from playwright.sync_api import sync_playwright, Page, Browser
from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry
from utils.har_loader import find_har_file, print_har_instructions
from extractors.weibo import WeiboExtractor


class WeiboScraper(BaseScraper):
    """微博用户抓取器 - 基于AJAX API + HAR回退"""

    def __init__(self, incremental: bool = False):
        existing_urls = None
        if incremental and config_manager.get("incremental_settings.enabled", True):
            extractor = WeiboExtractor()
            existing_urls = extractor.get_existing_urls()
            print(f"[INFO] 增量模式: 已存在 {len(existing_urls)} 条数据")

        weibo_url = config_manager.get("weibo_url")
        user_id = self._extract_user_id(weibo_url)

        scraper_config = ScraperConfig(
            url=weibo_url,
            output_filename="weibo_posts.html",
            headless=False,
            wait_seconds=config_manager.get("wait_seconds", 3),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0),
            incremental_mode=incremental,
            existing_urls=existing_urls,
            scraper_name="weibo",
            api_url_keywords=["mymblog", "statuses"],
            api_domain_filter="weibo.com",
            use_firefox_cookies=config_manager.get("weibo_settings.use_firefox_cookies", True),
        )
        super().__init__(scraper_config)

        self.user_id = user_id
        self.url_selector_template = f"a[href*='/{user_id}/']"

    def _extract_user_id(self, url: str) -> str:
        pattern = r'/u/(\d+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        return "6593199887"

    def _wait_for_login(self, page: Page) -> None:
        """等待登录完成（Cookie未生效时的兜底）"""
        try:
            feed_items = page.locator('.wbpro-scroller-item')
            if feed_items.count() > 0:
                return
        except:
            pass

        print("\n[INFO] Cookie未生效，等待用户手动登录微博...")
        print("[INFO] 请在浏览器中完成登录...")

        login_check_attempts = 0
        max_attempts = 90

        while login_check_attempts < max_attempts:
            try:
                feed_items = page.locator('.wbpro-scroller-item')
                if feed_items.count() > 0:
                    print(f"[INFO] 登录成功，检测到 {feed_items.count()} 条微博")
                    return
            except:
                pass

            login_check_attempts += 1
            time.sleep(2)

        print("[WARN] 等待超时，尝试继续抓取...")

    def _fetch_posts_via_api(self, page: Page) -> list:
        """通过微博AJAX API分页获取全部微博数据"""
        uid = self.user_id
        scroll_delay = self.config.scroll_delay
        incremental_enabled = self.config.incremental_mode and self.config.existing_urls
        stop_on_existing = config_manager.get("incremental_settings.stop_on_existing", True)

        all_posts = {}
        current_page = 1
        max_pages = 500
        last_report_count = 0

        print(f"[INFO] 开始通过API抓取微博 (uid={uid})...")

        request_context = page.request
        referer_url = f"https://weibo.com/u/{uid}"

        # 从 Cookie 中提取 XSRF-TOKEN（微博 API 必需）
        xsrf_token = ""
        try:
            cookies = page.context.cookies()
            for cookie in cookies:
                if cookie.get("name") == "XSRF-TOKEN":
                    xsrf_token = cookie.get("value", "")
                    break
            if xsrf_token:
                print(f"[INFO] 已获取 XSRF-TOKEN")
            else:
                print("[WARN] 未找到 XSRF-TOKEN，API 可能返回空数据")
        except Exception as e:
            print(f"[WARN] 获取 XSRF-TOKEN 失败: {e}")

        while current_page <= max_pages:
            try:
                api_url = f"https://weibo.com/ajax/statuses/mymblog?uid={uid}&page={current_page}&feature=0"
                headers = {
                    "Accept": "application/json, text/plain, */*",
                    "Referer": referer_url,
                    "X-Requested-With": "XMLHttpRequest",
                }
                if xsrf_token:
                    headers["X-XSRF-TOKEN"] = xsrf_token

                response = request_context.get(api_url, headers=headers)

                if not response.ok:
                    print(f"[WARN] API请求失败 (page={current_page}): HTTP {response.status}")
                    if current_page == 1:
                        print("[ERROR] 第一页请求失败，请确认已登录微博")
                    break

                result = response.json()

                # 调试：第一页打印响应结构
                if current_page == 1:
                    if isinstance(result, dict):
                        keys = list(result.keys())
                        print(f"[DEBUG] API响应顶层字段: {keys}")
                        if "data" in result and isinstance(result["data"], dict):
                            data_keys = list(result["data"].keys())
                            print(f"[DEBUG] data字段: {data_keys}")
                    else:
                        print(f"[DEBUG] API响应类型: {type(result).__name__}")
                        print(f"[DEBUG] 响应前200字符: {str(result)[:200]}")

                data = result.get("data", {}) if isinstance(result, dict) else {}
                post_list = data.get("list", []) if isinstance(data, dict) else []

                if not post_list:
                    print(f"[INFO] 第 {current_page} 页无数据，抓取完成")
                    if current_page == 1:
                        print("[DEBUG] 第一页就无数据，可能原因: Cookie过期/XSRF-TOKEN缺失/API结构变化")
                    break

                for post in post_list:
                    bid = post.get("bid", "")
                    if not bid:
                        continue

                    post_url = f"https://weibo.com/{uid}/{bid}"
                    if post_url not in all_posts:
                        user = post.get("user", {}) or {}
                        all_posts[post_url] = {
                            "time": post.get("created_at", ""),
                            "url": post_url,
                            "content": post.get("text_raw", post.get("text", "")),
                            "text_html": post.get("text", ""),
                            "source": post.get("source", ""),
                            "uid": uid,
                            "screen_name": user.get("screen_name", ""),
                            "profile_image_url": user.get("profile_image_url", ""),
                            "pic_infos": post.get("pic_infos"),
                            "retweeted_status": post.get("retweeted_status"),
                        }

                    if incremental_enabled and stop_on_existing:
                        if post_url in self.config.existing_urls:
                            print(f"[INFO] 发现已存在数据，增量模式停止 (已收集 {len(all_posts)} 条)")
                            return list(all_posts.values())

                total = data.get("total", 0)
                if len(all_posts) - last_report_count >= 100:
                    print(f"[INFO] 已收集 {len(all_posts)} 条微博 (第 {current_page} 页, 总计约 {total} 条)")
                    last_report_count = len(all_posts)

                current_page += 1
                time.sleep(scroll_delay)

            except Exception as e:
                print(f"[ERROR] API请求异常 (page={current_page}): {e}")
                break

        print(f"[INFO] API抓取完成，共收集 {len(all_posts)} 条微博")
        return list(all_posts.values())

    def _build_html(self, posts: list) -> str:
        """将收集的微博数据构建为完整HTML（与微博原始DOM结构一致）"""
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-cn" data-theme="light">',
            '<head>',
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1">',
            '<title>微博数据</title>',
            '<style>',
            'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #fff; margin: 0; }',
            '.wbpro-scroller-item { border-bottom: 1px solid #f0f0f0; padding: 16px 20px; }',
            'article { border-radius: 4px; }',
            '._body_ecgcn_63 { padding: 0; }',
            'header.woo-box-flex { display: flex; align-items: flex-start; margin-bottom: 12px; }',
            '.woo-avatar-main { width: 50px; height: 50px; border-radius: 50%; overflow: hidden; margin-right: 12px; flex-shrink: 0; }',
            '.woo-avatar-img { width: 100%; height: 100%; object-fit: cover; }',
            '._nick_ygi5b_25 a { color: #333; font-weight: 600; text-decoration: none; font-size: 15px; }',
            '._time_1tpft_33 { color: #939393; font-size: 13px; text-decoration: none; margin-right: 8px; }',
            '._source_1tpft_46 { color: #939393; font-size: 13px; }',
            '._wbtext_1h76l_19 { font-size: 15px; line-height: 1.6; color: #333; word-break: break-word; }',
            '._wbtext_1h76l_19 a { color: #ff6600; text-decoration: none; }',
            '._wbtext_1h76l_19 img { vertical-align: middle; max-width: 100%; }',
            '.wbpro-feed-content { margin-top: 8px; }',
            '.pic-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }',
            '.pic-list img { width: 120px; height: 120px; object-fit: cover; border-radius: 4px; }',
            '.retweet { background: #f7f7f7; border-radius: 4px; padding: 12px; margin-top: 12px; }',
            '.retweet ._wbtext_1h76l_19 { font-size: 14px; color: #666; }',
            '.retweet ._name_ygi5b_120 a { color: #eb7350; text-decoration: none; font-weight: 600; }',
            '</style>',
            '</head>',
            '<body>',
        ]

        for post in posts:
            html_parts.append(self._build_post_html(post))

        html_parts.append('</body></html>')
        return ''.join(html_parts)

    def _build_post_html(self, post: dict) -> str:
        """构建单条微博的完整HTML（与微博原始DOM结构一致）"""
        uid = post.get("uid", "")
        screen_name = html.escape(post.get("screen_name", ""))
        profile_image = html.escape(post.get("profile_image_url", ""))
        time_str = html.escape(post.get("time", ""))
        url = html.escape(post.get("url", ""))
        text_html = post.get("text_html", "") or html.escape(post.get("content", ""))
        source = html.escape(post.get("source", ""))

        # 日期显示：从 "2020-08-28 19:56" 提取 "2020-8-28"
        date_display = time_str
        date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', time_str)
        if date_match:
            m = int(date_match.group(2))
            d = int(date_match.group(3))
            date_display = f"{date_match.group(1)}-{m}-{d}"

        parts = [
            '<div class="wbpro-scroller-item">',
            '<article class="woo-panel-main _wrap_ecgcn_2 _normal_ecgcn_34" tabindex="0" style="border-radius: 4px;">',
            '<div class="_body_ecgcn_63">',
            # header: 头像 + 用户名 + 时间 + 来源
            '<header class="woo-box-flex">',
            f'<a href="//weibo.com/u/{uid}" aria-label="{screen_name}">',
            '<div class="woo-avatar-main woo-avatar-hover _avatar_ygi5b_15">',
            f'<img src="{profile_image}" class="woo-avatar-img" alt="{screen_name}">',
            '</div>',
            '</a>',
            '<div class="woo-box-item-flex _main_ygi5b_20">',
            '<div class="woo-box-flex woo-box-column woo-box-justifyCenter _content_wrap_ygi5b_114">',
            '<div class="woo-box-flex woo-box-alignCenter _nick_ygi5b_25">',
            f'<a href="//weibo.com/u/{uid}" class="_name_ygi5b_120"><span title="{screen_name}">{screen_name}</span></a>',
            '</div>',
            '<div class="woo-box-flex woo-box-alignCenter _info_1tpft_10">',
            f'<a class="_time_1tpft_33" title="{time_str}" href="{url}">{date_display}</a>',
        ]

        if source:
            parts.append('<div class="woo-box-item-flex _from_1tpft_24">')
            parts.append(f'<div class="_source_1tpft_46" title="来自 {source}">来自 {source}</div>')
            parts.append('</div>')

        parts.extend([
            '</div>',  # _info
            '</div>',  # _content_wrap
            '</div>',  # _main
            '</header>',
            # 正文内容
            '<div class="wbpro-feed-content">',
            '<div class="_text_1h76l_2 _ogText_1h76l_43 wbpro-feed-ogText">',
            f'<div class="_wbtext_1h76l_19">{text_html}</div>',
            '</div>',
        ])

        # 图片列表
        pic_infos = post.get("pic_infos")
        if pic_infos and isinstance(pic_infos, dict):
            parts.append('<div class="pic-list">')
            for pic_id, pic_info in pic_infos.items():
                if isinstance(pic_info, dict):
                    pic_url = pic_info.get("url", "")
                    if pic_url:
                        parts.append(f'<img src="{html.escape(pic_url)}" alt="">')
            parts.append('</div>')

        # 转发内容
        retweeted = post.get("retweeted_status")
        if retweeted and isinstance(retweeted, dict):
            rt_user = retweeted.get("user", {}) or {}
            rt_name = html.escape(rt_user.get("screen_name", ""))
            rt_text = retweeted.get("text", "")
            rt_uid = rt_user.get("idstr", "")
            parts.append('<div class="retweet">')
            if rt_name:
                parts.append(f'<span class="_name_ygi5b_120"><a href="//weibo.com/u/{rt_uid}">{rt_name}</a></span>: ')
            parts.append(f'<div class="_wbtext_1h76l_19">{rt_text}</div>')
            parts.append('</div>')

        parts.extend([
            '</div>',  # wbpro-feed-content
            '</div>',  # _body
            '</article>',
            '</div>',  # wbpro-scroller-item
        ])

        return ''.join(parts)

    def _process_page(self, page: Page) -> str:
        """处理页面：API抓取 → 失败则HAR回退"""
        page.goto(self.config.url, timeout=self.config.timeout)
        try:
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        time.sleep(self.config.wait_seconds)

        self._wait_for_login(page)

        posts = self._fetch_posts_via_api(page)

        if posts:
            return self._build_html(posts)

        # API未获取到数据
        print("\n[WARN] API抓取未获取到数据")
        har_path = find_har_file(self.config.scraper_name)
        if har_path:
            print(f"[INFO] 检测到HAR文件: {har_path}")
            print("[INFO] 请删除HAR文件后重新运行，或手动检查API配置")
        else:
            print_har_instructions(
                self.config.scraper_name,
                self.config.url,
                ["weibo.com/ajax"]
            )

        # 回退到DOM抓取
        print("[INFO] 回退到DOM抓取模式...")
        return page.content()

    def _check_existing_urls(self, page: Page) -> bool:
        try:
            current_urls = page.evaluate(f"""
                Array.from(document.querySelectorAll('{self.url_selector_template}'))
                    .map(el => el.href)
                    .filter(url => url && url.includes('/{self.user_id}/'))
            """)

            for url in current_urls:
                if url in self.config.existing_urls:
                    print(f"[INFO] 检测到已存在URL: {url}")
                    return True

            return False

        except Exception as e:
            print(f"[WARN] URL检测失败: {e}")
            return False


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(incremental: bool = False):
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}抓取微博用户主页")

    scraper = WeiboScraper(incremental=incremental)
    html_content = scraper.run()

    if html_content:
        print("[OK] 微博用户主页抓取完成")
        return html_content
    else:
        print("[ERROR] 微博用户主页抓取失败")
        return None


if __name__ == "__main__":
    run()
