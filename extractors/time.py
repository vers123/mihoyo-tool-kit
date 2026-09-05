import re
import os
from datetime import datetime, timedelta
from typing import List, Set
from dataclasses import dataclass
from core.config_manager import config_manager
from utils.error_handler import handle_errors, ErrorHandler
from utils.backup_manager import backup_manager


@dataclass
class PostData:
    date: str
    title: str
    url: str
    index: int = 0

    def __hash__(self):
        return hash((self.date, self.title, self.url))


class PostExtractor:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.html_path = os.path.join(
            config_manager.get_output_dir("html"),
            config_manager.get_filename("user_html")
        )
        self.output_dir = config_manager.get_output_dir("data")
        self.output_path = os.path.join(
            self.output_dir,
            config_manager.get_filename("posts_data")
        )

    def load_existing_data(self) -> List[PostData]:
        """加载已存在的数据"""
        if not os.path.exists(self.output_path):
            return []

        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                content = f.read()

            items = []
            pattern = re.compile(r'\d{4}-(.+?)-\[(\d{4}-\d{2}-\d{2})\]\((https://.+?)\)')

            for match in pattern.findall(content):
                title = match[0].strip()
                date = match[1]
                url = match[2]
                items.append(PostData(date=date, title=title, url=url))

            print(f"[INFO] 已加载 {len(items)} 条旧数据")
            return items

        except Exception as e:
            print(f"[WARN] 加载旧数据失败: {e}")
            return []

    def get_existing_urls(self) -> Set[str]:
        """获取已存在的URL集合"""
        existing_data = self.load_existing_data()
        return {item.url for item in existing_data}

    def extract_posts(self, html_content: str = None, incremental: bool = False) -> List[PostData]:
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                return []

            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        now = datetime.now()
        current_year = now.year

        pattern = re.compile(
            r'<div class="mhy-account-center-post-card">([\s\S]*?)</div>\s*</div>',
            re.DOTALL
        )

        items = []
        for post_block in pattern.findall(html_content):
            time_match = re.search(r'class="mhy-account-center-time__small">([^<]+)<', post_block)
            url_match = re.search(r'href="(/ys/article/\d+)"', post_block)
            title_match = re.search(r'class="mhy-article-card__h3"[^>]*>([\s\S]*?)</h3>', post_block)

            if not time_match or not url_match or not title_match:
                continue

            time_str = time_match.group(1).strip()
            if ' · ' in time_str:
                time_str = time_str.split(' · ')[0]

            url = f"https://www.miyoushe.com{url_match.group(1)}"
            title = title_match.group(1).strip()
            title = re.sub(r'\s+', ' ', title)

            final_date = self._parse_date(time_str, now, current_year)

            items.append(PostData(date=final_date, title=title, url=url))

        # 增量合并模式
        if incremental and config_manager.get("incremental_settings.merge_data", True):
            existing_data = self.load_existing_data()
            items = self._merge_data(existing_data, items)
            print(f"[INFO] 增量合并完成，共 {len(items)} 条数据")

        items = sorted(set(items), key=lambda x: x.date, reverse=True)

        for idx, item in enumerate(items, 1):
            item.index = idx

        return items

    def _merge_data(self, old_data: List[PostData], new_data: List[PostData]) -> List[PostData]:
        """合并新旧数据"""
        # 使用URL作为唯一标识去重
        merged = {item.url: item for item in old_data}

        # 新数据覆盖旧数据（保持最新）
        for item in new_data:
            merged[item.url] = item

        return list(merged.values())

    def _parse_date(self, time_str: str, now: datetime, current_year: int) -> str:
        if "小时前" in time_str:
            h = int(re.findall(r'(\d+)小时前', time_str)[0])
            return (now - timedelta(hours=h)).strftime("%Y-%m-%d")
        elif re.match(r'\d{2}-\d{2}', time_str):
            return f"{current_year}-{time_str}"
        else:
            return time_str

    def save_post_data(self, post_data: List[PostData]) -> bool:
        if not ErrorHandler.validate_directory_exists(self.output_dir):
            return False

        # 备份旧数据
        if config_manager.get("backup_settings.enabled", True) and os.path.exists(self.output_path):
            backup_manager.create_backup(self.output_path)

        lines = []
        for item in post_data:
            lines.append(f"{item.index:04d}-{item.title}-[{item.date}]({item.url})")

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(lines))
            return True
        except Exception as e:
            print(f"[ERROR] 保存帖子数据失败: {e}")
            return False


@handle_errors
def run(incremental: bool = False):
    """运行帖子提取，支持增量模式"""
    mode = "增量" if incremental else "全量"
    print(f"\n[START] {mode}提取帖子数据")

    extractor = PostExtractor()
    post_data = extractor.extract_posts(incremental=incremental)

    if not post_data:
        print("[ERROR] 未找到帖子数据")
        print(f"[HINT] 请先执行「抓取用户发帖主页」生成 {extractor.html_path}")
        return

    if extractor.save_post_data(post_data):
        print(f"[OK] 完成！共 {len(post_data)} 条帖子")
        print(f"[OK] 已保存到：{extractor.output_path}")
    else:
        print("[ERROR] 保存帖子数据失败")


if __name__ == "__main__":
    run()
