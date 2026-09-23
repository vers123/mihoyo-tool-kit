from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class TutorialScraper(BaseScraper):
    def __init__(self, tutorial_id: str = None):
        if not tutorial_id:
            tutorial_id = "mh4imrrhzdzi"

        url = f"https://act.mihoyo.com/ys/ugc/tutorial/detail/{tutorial_id}"

        scraper_config = ScraperConfig(
            url=url,
            output_filename=f"tutorial_{tutorial_id}.html",
            headless=config_manager.get("headless", False),
            wait_seconds=config_manager.get("wait_seconds", 5),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0)
        )
        super().__init__(scraper_config)
        self.tutorial_id = tutorial_id


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run(tutorial_id: str = None):
    scraper = TutorialScraper(tutorial_id)
    html_content = scraper.run()

    if html_content:
        print("[OK] 教程页面抓取完成")
        return html_content
    else:
        print("[ERROR] 教程页面抓取失败")
        return None


def run_tutorial_batch(index_id: str = None):
    """抓取目录索引页，提取所有教程链接，逐个抓取所有教程详情页"""
    if not index_id:
        index_id = "mhs2w008wf14"

    print(f"\n[START] 批量抓取教程页面，索引ID: {index_id}")
    print(f"[INFO] 索引页: https://act.mihoyo.com/ys/ugc/tutorial/detail/{index_id}")

    # 1. 抓取索引页
    print("\n[STEP 1/3] 抓取索引页...")
    html_content = run(index_id)
    if not html_content:
        print("[ERROR] 索引页抓取失败，无法继续")
        return

    # 2. 提取所有教程链接
    print("\n[STEP 2/3] 提取教程链接...")
    from extractors.tutorial import ChangelogExtractor
    if not ChangelogExtractor.is_changelog(html_content):
        print("[WARN] 该页面不是更新日志/目录页，无法提取链接")
        return

    extractor = ChangelogExtractor(index_id)
    links = extractor.extract_all_links(html_content)
    if not links:
        print("[ERROR] 未提取到任何教程链接")
        return

    print(f"[OK] 共发现 {len(links)} 个教程页面")

    # 3. 逐个抓取
    print(f"\n[STEP 3/3] 开始批量抓取 {len(links)} 个教程页面...")
    success_count = 0
    skip_count = 0
    fail_count = 0

    import os
    html_dir = config_manager.get_output_dir("html")

    for i, link in enumerate(links, 1):
        tid = link["tutorial_id"]
        title = link["title"]
        html_path = os.path.join(html_dir, f"tutorial_{tid}.html")

        # 跳过已存在的文件
        if os.path.exists(html_path):
            print(f"  [{i}/{len(links)}] 跳过（已存在）: {title} ({tid})")
            skip_count += 1
            continue

        print(f"  [{i}/{len(links)}] 抓取: {title} ({tid})")
        try:
            sub_html = run(tid)
            if sub_html:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"  [ERROR] 抓取失败: {tid} - {e}")
            fail_count += 1

    print(f"\n[DONE] 批量抓取完成: 新增 {success_count}，跳过 {skip_count}，失败 {fail_count}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tutorial_id = sys.argv[1]
        run(tutorial_id)
    else:
        run()
