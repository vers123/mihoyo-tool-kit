"""
原神英文版新闻提取器
从原神英文版新闻 HTML 中提取标题、日期、分类、摘要、封面图、链接等数据
"""

from typing import List
from .base import GameNewsBaseExtractor, NewsItem
from core.config_manager import config_manager
from utils.error_handler import handle_errors


class GenshinENNewsExtractor(GameNewsBaseExtractor):
    """原神英文版新闻提取器"""

    game_key = "genshin_en"

    def __init__(self):
        super().__init__()

    def _parse_html_fallback(self, html_content: str) -> List[NewsItem]:
        """原神英文版特有的 DOM 宽松匹配"""
        import re
        items = []
        seen_urls = set()

        pattern_full = re.compile(
            r'<li class="news__item[^"]*">\s*<a href="(/en/news/detail/\d+)"[^>]*class="news__title[^"]*"[^>]*>'
            r'.*?<h3[^>]*title="([^"]*)"[^>]*>([^<]+)</h3>.*?'
            r'<div class="news__date">([^<]+)</div>',
            re.DOTALL
        )

        for match in pattern_full.findall(html_content):
            url_path = match[0]
            title_attr = match[1]
            title_text = match[2].strip()
            date = match[3].strip()

            url = self._resolve_url(url_path)
            title = title_attr if title_attr else title_text
            title = re.sub(r'\s+', ' ', title)

            if url not in seen_urls:
                seen_urls.add(url)
                items.append(NewsItem(title=title, date=date, url=url))

        pattern_loose = re.compile(
            r'<li class="news__item[^"]*">.*?'
            r'<a href="(/en/news/detail/\d+)"[^>]*class="news__title[^"]*"[^>]*>'
            r'.*?<h3[^>]*>([^<]+)</h3>.*?'
            r'<div class="news__date">([^<]+)</div>',
            re.DOTALL
        )

        for match in pattern_loose.findall(html_content):
            url_path = match[0]
            title_text = match[1].strip()
            date = match[2].strip()
            url = self._resolve_url(url_path)
            title = re.sub(r'\s+', ' ', title_text)

            if url not in seen_urls:
                seen_urls.add(url)
                items.append(NewsItem(title=title, date=date, url=url))

        return items


@handle_errors
def run(incremental: bool = False):
    """运行原神英文版新闻提取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}提取原神英文版新闻数据")

    extractor = GenshinENNewsExtractor()
    news_data = extractor.extract_news(incremental=incremental)

    if not news_data:
        print("[ERROR] 未找到新闻数据或HTML文件不存在")
        return

    if extractor.save_news_data(news_data):
        print(f"[OK] 完成！共 {len(news_data)} 条新闻")
        print(f"[OK] 已保存到：{extractor.output_path}")
    else:
        print("[ERROR] 保存新闻数据失败")


if __name__ == "__main__":
    run()
