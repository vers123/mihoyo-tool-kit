"""
新闻提取公共基类
基于 content_v2_user 统一 API 架构生成的 HTML 提取数据

提取格式（7字段）：
序号-标题-[日期]-[分类]-[摘要]-[封面图URL]-(完整URL)

兼容原神旧格式（4字段）：序号-标题-[日期]-(URL)
"""

import re
import os
from typing import List, Set, Optional
from dataclasses import dataclass, field
from core.config_manager import config_manager
from utils.error_handler import handle_errors, ErrorHandler
from utils.backup_manager import backup_manager


@dataclass
class NewsItem:
    """新闻数据项"""
    iInfoId: str = ""
    title: str = ""
    date: str = ""
    category: str = ""
    intro: str = ""
    poster_url: str = ""
    url: str = ""
    index: int = 0

    def __hash__(self):
        return hash(self.url) if self.url else hash((self.title, self.date))

    def __eq__(self, other):
        if not isinstance(other, NewsItem):
            return False
        if self.url and other.url:
            return self.url == other.url
        return self.title == other.title and self.date == other.date


class GameNewsBaseExtractor:
    """游戏新闻提取器基类

    子类需要覆盖：
    - game_key: 游戏标识
    - html_pattern: HTML 提取正则表达式
    - url_base: URL 基础域名（用于补全相对路径）
    """

    game_key: str = ""

    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

        site_config = config_manager.get_news_config(self.game_key)
        if not site_config:
            raise ValueError(f"未找到游戏 '{self.game_key}' 的新闻配置")

        self.site_config = site_config
        self.html_dir = config_manager.get_news_output_dir(self.game_key, "html")
        self.data_dir = config_manager.get_news_output_dir(self.game_key, "data")

        self.html_path = os.path.join(self.html_dir, site_config["html_filename"])
        self.output_path = os.path.join(self.data_dir, site_config["data_filename"])

        # URL 基础域名
        from urllib.parse import urlparse
        parsed = urlparse(site_config["url"])
        self.url_base = f"{parsed.scheme}://{parsed.netloc}"

    # ---- 加载已有数据 ----

    def load_existing_data(self) -> List[NewsItem]:
        """加载已存在的数据（兼容新旧格式）"""
        if not os.path.exists(self.output_path):
            return []

        try:
            with open(self.output_path, "r", encoding="utf-8") as f:
                content = f.read()

            items = []

            # 新格式（7字段）：序号-标题-[日期]-[分类]-[摘要]-[封面图]-(URL)
            pattern_new = re.compile(
                r'^\d{4}-(.+?)-\[(.+?)\]-\[(.*?)\]-\[(.*?)\]-\[(.*?)\]-\((https?://.+?)\)',
                re.MULTILINE
            )
            for match in pattern_new.findall(content):
                items.append(NewsItem(
                    title=match[0].strip(),
                    date=match[1].strip(),
                    category=match[2].strip(),
                    intro=match[3].strip(),
                    poster_url=match[4].strip(),
                    url=match[5].strip(),
                ))

            # 如果新格式没匹配到，尝试旧格式（4字段）：序号-标题-[日期]-(URL)
            if not items:
                pattern_old = re.compile(
                    r'^\d{4}-(.+?)-\[(.+?)\]-\((https?://.+?)\)',
                    re.MULTILINE
                )
                for match in pattern_old.findall(content):
                    items.append(NewsItem(
                        title=match[0].strip(),
                        date=match[1].strip(),
                        url=match[2].strip(),
                    ))

            print(f"[INFO] 已加载 {len(items)} 条旧数据")
            return items

        except Exception as e:
            print(f"[WARN] 加载旧数据失败: {e}")
            return []

    def get_existing_urls(self) -> Set[str]:
        """获取已存在的 URL 集合"""
        existing_data = self.load_existing_data()
        return {item.url for item in existing_data if item.url}

    # ---- 提取逻辑 ----

    def extract_news(self, html_content: str = None, incremental: bool = False) -> List[NewsItem]:
        """从 HTML 中提取新闻数据

        安全策略：
        - 只要本地数据文件存在，始终将新提取数据与旧数据合并去重后再写入，
          避免增量抓取后 HTML 只含新数据时覆盖完整历史。
        - 若 HTML 未解析到任何新数据，但本地已有数据，则直接返回旧数据
          （调用方据此跳过写入，保留原文件不变）。

        Args:
            html_content: HTML 内容，为 None 时从文件读取
            incremental: 兼容参数（保留），不再控制合并行为；合并始终开启

        Returns:
            合并去重后的新闻列表；无新数据且无旧数据时返回空列表
        """
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                return []

            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        new_items = self._parse_html(html_content)
        self._has_new_data = bool(new_items)

        # 始终加载已有数据（只要文件存在），用于合并
        existing_data = self.load_existing_data()

        if not new_items:
            print("[WARN] 未提取到新闻数据")
            if existing_data:
                print(f"[INFO] 本地已有 {len(existing_data)} 条数据，保留原文件不覆盖")
                return existing_data
            return []

        # 合并新旧数据（新数据覆盖同 URL 的旧数据）
        items = self._merge_data(existing_data, new_items)
        print(f"[INFO] 合并完成：新 {len(new_items)} 条 + 旧 {len(existing_data)} 条 = {len(items)} 条")

        # 去重并按日期倒序
        items = sorted(set(items), key=lambda x: x.date, reverse=True)

        for idx, item in enumerate(items, 1):
            item.index = idx

        print(f"[INFO] 成功提取 {len(items)} 条新闻")
        if items:
            print(f"[INFO] 第一条新闻: {items[0].date} - {items[0].title}")
            print(f"[INFO] 最后一条新闻: {items[-1].date} - {items[-1].title}")

        return items

    def _parse_html(self, html_content: str) -> List[NewsItem]:
        """解析 HTML 提取新闻数据

        优先从结构化的 data-* 属性中提取（API 构建的 HTML），
        失败则回退到 DOM 选择器提取。
        """
        items = []

        # 策略1：从 li[data-id] 结构化属性提取
        # 先找到所有 news__item 块
        item_pattern = re.compile(
            r'<li class="news__item" data-id="(\d+)">(.*?)</li>',
            re.DOTALL
        )

        for match in item_pattern.finditer(html_content):
            info_id = match.group(1).strip()
            item_html = match.group(2)

            # 提取封面图
            poster = ""
            poster_match = re.search(
                r'<div class="news__poster"><img src="([^"]*)"',
                item_html
            )
            if poster_match:
                poster = poster_match.group(1).strip()

            # 提取分类
            category = ""
            category_match = re.search(
                r'<span class="news__category">([^<]*)</span>',
                item_html
            )
            if category_match:
                category = category_match.group(1).strip()

            # 提取标题链接和标题
            url_path = ""
            title_attr = ""
            title_text = ""
            title_match = re.search(
                r'<a href="([^"]*)" class="news__title">.*?'
                r'<h3[^>]*title="([^"]*)"[^>]*>([^<]*)</h3>',
                item_html,
                re.DOTALL
            )
            if title_match:
                url_path = title_match.group(1).strip()
                title_attr = title_match.group(2).strip()
                title_text = title_match.group(3).strip()

            # 提取摘要
            intro = ""
            intro_match = re.search(
                r'<p class="news__intro">([^<]*)</p>',
                item_html
            )
            if intro_match:
                intro = intro_match.group(1).strip()

            # 提取日期
            date = ""
            date_match = re.search(
                r'<div class="news__date">([^<]*)</div>',
                item_html
            )
            if date_match:
                date = date_match.group(1).strip()

            title = title_attr if title_attr else title_text
            title = re.sub(r'\s+', ' ', title).strip()

            # 补全 URL
            url = self._resolve_url(url_path)

            if not title or not url:
                continue

            item = NewsItem(
                iInfoId=info_id,
                title=title,
                date=date,
                category=category,
                intro=intro,
                poster_url=poster,
                url=url,
            )

            if not any(i.url == url and i.title == title for i in items):
                items.append(item)

        # 如果结构化提取没结果，尝试宽松 DOM 匹配（兼容老页面）
        if not items:
            items = self._parse_html_fallback(html_content)

        return items

    def _parse_html_fallback(self, html_content: str) -> List[NewsItem]:
        """宽松模式 DOM 提取（兜底）

        子类可覆盖此方法以适配特定网站的 DOM 结构。
        """
        items = []
        # 默认宽松匹配：查找所有包含 news__item 类的 li，提取链接、标题、日期
        pattern = re.compile(
            r'<li[^>]*class="[^"]*news__item[^"]*"[^>]*>.*?'
            r'<a href="([^"]*)"[^>]*class="[^"]*news__title[^"]*"[^>]*>.*?'
            r'<h3[^>]*>([^<]+)</h3>.*?'
            r'<div[^>]*class="[^"]*news__date[^"]*"[^>]*>([^<]+)</div>',
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

    def _resolve_url(self, url_path: str) -> str:
        """补全 URL 为完整路径"""
        if url_path.startswith("http"):
            return url_path
        if url_path.startswith("//"):
            return "https:" + url_path
        if url_path.startswith("/"):
            return self.url_base + url_path
        return self.url_base + "/" + url_path

    # ---- 合并与保存 ----

    def _merge_data(self, old_data: List[NewsItem], new_data: List[NewsItem]) -> List[NewsItem]:
        """合并新旧数据（新数据覆盖旧数据）"""
        merged = {item.url: item for item in old_data if item.url}
        # 没有 url 的用 title+date 作为 key
        for item in old_data:
            if not item.url:
                key = f"{item.title}|{item.date}"
                merged[key] = item

        for item in new_data:
            if item.url:
                merged[item.url] = item
            else:
                key = f"{item.title}|{item.date}"
                merged[key] = item

        return list(merged.values())

    def save_news_data(self, news_data: List[NewsItem]) -> bool:
        """保存新闻数据到文件"""
        if not ErrorHandler.validate_directory_exists(self.data_dir):
            return False

        # 备份旧数据
        if config_manager.get("backup_settings.enabled", True) and os.path.exists(self.output_path):
            backup_manager.create_backup(self.output_path)

        lines = []
        for item in news_data:
            # 新格式：序号-标题-[日期]-[分类]-[摘要]-[封面图]-(URL)
            lines.append(
                f"{item.index:04d}-{item.title}"
                f"-[{item.date}]"
                f"-[{item.category}]"
                f"-[{item.intro}]"
                f"-[{item.poster_url}]"
                f"-({item.url})"
            )

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception as e:
            print(f"[ERROR] 保存新闻数据失败: {e}")
            return False
