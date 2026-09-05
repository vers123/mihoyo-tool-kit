import re
import os
import html
from datetime import datetime, timedelta
from typing import List, Set
from dataclasses import dataclass
from core.config_manager import config_manager
from utils.error_handler import handle_errors, ErrorHandler
from utils.backup_manager import backup_manager


@dataclass
class WeiboData:
    date: str
    content: str
    url: str
    index: int = 0

    def __hash__(self):
        return hash((self.date, self.content, self.url))


class WeiboExtractor:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.html_path = os.path.join(
            config_manager.get_output_dir("html"),
            config_manager.get_filename("weibo_html")
        )
        self.output_dir = config_manager.get_output_dir("data")
        self.output_path = os.path.join(
            self.output_dir,
            config_manager.get_filename("weibo_data")
        )

    def load_existing_data(self) -> List[WeiboData]:
        if not os.path.exists(self.output_path):
            return []

        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                content = f.read()

            items = []
            pattern = re.compile(r'\d{4}-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://.+?)\)')

            for match in pattern.findall(content):
                content_text = match[0].strip()
                date = match[1]
                url = match[2]
                items.append(WeiboData(date=date, content=content_text, url=url))

            print(f"[INFO] 已加载 {len(items)} 条旧数据")
            return items

        except Exception as e:
            print(f"[WARN] 加载旧数据失败: {e}")
            return []

    def get_existing_urls(self) -> Set[str]:
        existing_data = self.load_existing_data()
        return {item.url for item in existing_data}

    def extract_weibo(self, html_content: str = None, incremental: bool = False) -> List[WeiboData]:
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                return []

            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        items = []

        time_url_pattern = re.compile(
            r'<a class="_time_[^"]*"\s+title="([^"]+)"\s+href="(https://weibo\.com/\d+/[A-Za-z0-9]+)"'
        )

        matches = list(time_url_pattern.finditer(html_content))

        for match in matches:
            time_str = match.group(1).strip()
            url = match.group(2)

            content = self._extract_content_for_url(html_content, match.end())

            if not content:
                continue

            final_date = self._parse_date(time_str)

            items.append(WeiboData(date=final_date, content=content, url=url))

        if not items:
            print("[WARN] 主模式未匹配，尝试备用模式")
            alt_pattern = re.compile(
                r'href="(https://weibo\.com/\d+/[A-Za-z0-9]+)"[^>]*>\s*([^<]*(?:今天|昨天|前天|\d+月\d+日|\d{4}-\d{2}-\d{2})[^<]*)'
            )
            for match in alt_pattern.finditer(html_content):
                url = match.group(1)
                time_str = match.group(2).strip()
                content = self._extract_content_for_url(html_content, match.end())
                if content:
                    final_date = self._parse_date(time_str)
                    items.append(WeiboData(date=final_date, content=content, url=url))

        if incremental and config_manager.get("incremental_settings.merge_data", True):
            existing_data = self.load_existing_data()
            items = self._merge_data(existing_data, items)
            print(f"[INFO] 增量合并完成，共 {len(items)} 条数据")

        seen_urls = set()
        unique_items = []
        for item in items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)

        unique_items = sorted(unique_items, key=lambda x: x.date, reverse=True)

        for idx, item in enumerate(unique_items, 1):
            item.index = idx

        return unique_items

    def _extract_content_for_url(self, html_content: str, start_pos: int) -> str:
        search_region = html_content[start_pos:start_pos + 5000]

        content_pattern = re.compile(
            r'<div class="_wbtext_[^"]*">(.*?)</div>',
            re.DOTALL
        )

        match = content_pattern.search(search_region)
        if match:
            content = match.group(1).strip()
            content = re.sub(r'<[^>]+>', '', content)
            content = html.unescape(content)
            content = re.sub(r'\s+', ' ', content)
            return content.strip()

        return ""

    def _merge_data(self, old_data: List[WeiboData], new_data: List[WeiboData]) -> List[WeiboData]:
        merged = {item.url: item for item in old_data}

        for item in new_data:
            merged[item.url] = item

        return list(merged.values())

    def _parse_date(self, time_str: str) -> str:
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', time_str)
        if date_match:
            return date_match.group(1)

        now = datetime.now()
        current_year = now.year

        if "分钟前" in time_str:
            m = int(re.findall(r'(\d+)分钟前', time_str)[0])
            return (now - timedelta(minutes=m)).strftime("%Y-%m-%d")
        elif "小时前" in time_str:
            h = int(re.findall(r'(\d+)小时前', time_str)[0])
            return (now - timedelta(hours=h)).strftime("%Y-%m-%d")
        elif "昨天" in time_str:
            return (now - timedelta(days=1)).strftime("%Y-%m-%d")
        elif "前天" in time_str:
            return (now - timedelta(days=2)).strftime("%Y-%m-%d")
        elif re.match(r'\d{2}-\d{2}', time_str):
            return f"{current_year}-{time_str}"
        else:
            return time_str

    def save_weibo_data(self, weibo_data: List[WeiboData]) -> bool:
        if not ErrorHandler.validate_directory_exists(self.output_dir):
            return False

        if config_manager.get("backup_settings.enabled", True) and os.path.exists(self.output_path):
            backup_manager.create_backup(self.output_path)

        lines = []
        for item in weibo_data:
            lines.append(f"{item.index:04d}-{item.content}-[{item.date}]({item.url})")

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(lines))
            return True
        except Exception as e:
            print(f"[ERROR] 保存微博数据失败: {e}")
            return False


@handle_errors
def run(incremental: bool = False):
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}提取微博数据")

    extractor = WeiboExtractor()
    weibo_data = extractor.extract_weibo(incremental=incremental)

    if not weibo_data:
        print("[ERROR] 未找到微博数据")
        print(f"[HINT] 请先执行「抓取微博用户主页」生成 {extractor.html_path}")
        return

    if extractor.save_weibo_data(weibo_data):
        print(f"[OK] 完成！共 {len(weibo_data)} 条微博")
        print(f"[OK] 已保存到：{extractor.output_path}")
    else:
        print("[ERROR] 保存微博数据失败")


if __name__ == "__main__":
    run()