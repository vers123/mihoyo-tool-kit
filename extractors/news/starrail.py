"""
星穹铁道新闻提取器
从星穹铁道新闻 HTML 中提取标题、日期、分类、摘要、封面图、链接等数据
"""

from typing import List
from .base import GameNewsBaseExtractor, NewsItem
from core.config_manager import config_manager
from utils.error_handler import handle_errors


class SRNewsExtractor(GameNewsBaseExtractor):
    """星穹铁道新闻提取器"""

    game_key = "starrail"

    def __init__(self):
        super().__init__()

    def _parse_html_fallback(self, html_content: str) -> List[NewsItem]:
        """星穹铁道特有的 DOM 宽松匹配（兜底用）"""
        import re
        items = []

        # 尝试多种可能的 DOM 结构
        patterns = [
            # 模式1：带 news-item 类的列表项
            re.compile(
                r'<(?:li|div)[^>]*class="[^"]*news-item[^"]*"[^>]*>.*?'
                r'<a[^>]*href="(/news/\d+)"[^>]*>.*?'
                r'(?:<h[1-6][^>]*>([^<]+)</h[1-6]>).*?'
                r'(?:<(?:div|span)[^>]*class="[^"]*date[^"]*"[^>]*>([^<]+)</(?:div|span)>)',
                re.DOTALL
            ),
            # 模式2：带 type-item 类的分类项
            re.compile(
                r'<(?:li|div)[^>]*class="[^"]*type-item[^"]*"[^>]*>.*?'
                r'<a[^>]*href="(/news/\d+)"[^>]*>.*?'
                r'<(?:div|span)[^>]*>([^<]+)</(?:div|span)>',
                re.DOTALL
            ),
        ]

        for pattern in patterns:
            for match in pattern.findall(html_content):
                url_path = match[0].strip()
                title = re.sub(r'\s+', ' ', match[1].strip())
                date = match[2].strip() if len(match) > 2 else ""

                url = self._resolve_url(url_path)
                item = NewsItem(title=title, date=date, url=url)
                if not any(i.url == url and i.title == title for i in items):
                    items.append(item)

            if items:
                break

        return items


@handle_errors
def run(incremental: bool = False):
    """运行星穹铁道新闻提取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}提取星穹铁道新闻数据")

    extractor = SRNewsExtractor()
    news_data = extractor.extract_news(incremental=incremental)

    if not news_data:
        print("[ERROR] 未找到新闻数据")
        print(f"[HINT] 请先执行「抓取星穹铁道新闻页面」生成 {extractor.html_path}")
        return

    if extractor.save_news_data(news_data):
        print(f"[OK] 完成！共 {len(news_data)} 条新闻")
        print(f"[OK] 已保存到：{extractor.output_path}")
    else:
        print("[ERROR] 保存新闻数据失败")


if __name__ == "__main__":
    run()
