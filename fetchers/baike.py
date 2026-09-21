from core.scraper import BaseScraper, ScraperConfig
from core.config_manager import config_manager
from utils.error_handler import handle_errors, retry


class BaikeScraper(BaseScraper):
    def __init__(self):
        scraper_config = ScraperConfig(
            url=config_manager.get("baike_url"),
            output_filename="character_list.html",
            headless=config_manager.get("headless", False),
            wait_seconds=config_manager.get("wait_seconds", 3),
            timeout=config_manager.get("timeout", 120000),
            user_agent=config_manager.get("user_agent"),
            browser_args=config_manager.get("browser_args", []),
            scroll_delay=config_manager.get("scroll_settings.delay", 2.0)
        )
        super().__init__(scraper_config)


@handle_errors
@retry(max_attempts=config_manager.get("retry_settings.max_attempts", 3),
       delay=config_manager.get("retry_settings.delay", 2.0))
def run():
    scraper = BaikeScraper()
    html_content = scraper.run()

    if html_content:
        print("[OK] 角色图鉴页面抓取完成")
        return html_content
    else:
        print("[ERROR] 角色图鉴页面抓取失败")
        return None


if __name__ == "__main__":
    run()
