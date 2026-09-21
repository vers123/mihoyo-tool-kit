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


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tutorial_id = sys.argv[1]
        run(tutorial_id)
    else:
        run()
