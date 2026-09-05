"""
绝区零新闻提取器
从绝区零新闻 HTML 中提取标题、日期、分类、摘要、封面图、链接等数据
"""

from typing import List
from .base import GameNewsBaseExtractor, NewsItem
from core.config_manager import config_manager
from utils.error_handler import handle_errors


class ZZZNewsExtractor(GameNewsBaseExtractor):
    """绝区零新闻提取器"""

    game_key = "zzz"

    def __init__(self):
        super().__init__()

    def _parse_html_fallback(self, html_content: str) -> List[NewsItem]:
        """绝区零特有的 DOM 宽松匹配（兜底用）"""
        import re
        items = []

        # 绝区零 DOM 结构：news-list__item / news-list__item-title / news-list__item-date
        pattern = re.compile(
            r'<div[^>]*class="[^"]*news-list__item[^"]*"[^>]*>.*?'
            r'<a[^>]*href="(/news/\d+)"[^>]*>.*?'
            r'(?:<div[^>]*class="[^"]*news-list__item-title[^"]*"[^>]*>([^<]+)</div>.*?'
            r'<div[^>]*class="[^"]*news-list__item-date[^"]*"[^>]*>([^<]+)</div>)',
            re.DOTALL
        )

        for match in pattern.findall(html_content):
            url_path = match[0].strip()
            title = re.sub(r'\s+', ' ', match[1].strip())
            date = match[2].strip()

            url = self._resolve_url(url_path)
            item = NewsItem(title=title, date=date, url=url)
            if not any(i.url == url and i.title == title for i in items):
                items.append(item)

        return items


@handle_errors
def run(incremental: bool = False):
    """运行绝区零新闻提取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}提取绝区零新闻数据")

    extractor = ZZZNewsExtractor()
    news_data = extractor.extract_news(incremental=incremental)

    if not news_data:
        print("[ERROR] 未找到新闻数据")
        print(f"[HINT] 请先执行「抓取绝区零新闻页面」生成 {extractor.html_path}")
        return

    if extractor.save_news_data(news_data):
        print(f"[OK] 完成！共 {len(news_data)} 条新闻")
        print(f"[OK] 已保存到：{extractor.output_path}")
    else:
        print("[ERROR] 保存新闻数据失败")


if __name__ == "__main__":
    run()
