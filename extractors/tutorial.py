import re
import os
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from core.config_manager import config_manager
from utils.error_handler import handle_errors, ErrorHandler


@dataclass
class CharacterData:
    id: str
    name: str
    index: int = 0

    def __hash__(self):
        return hash((self.id, self.name))


class TutorialExtractor:
    def __init__(self, tutorial_id: str = None):
        self.base_dir = os.path.dirname(__file__)

        if not tutorial_id:
            tutorial_id = "mh4imrrhzdzi"

        self.html_path = os.path.join(
            config_manager.get_output_dir("html"),
            f"tutorial_{tutorial_id}.html"
        )
        self.output_dir = config_manager.get_output_dir("data")
        self.output_path = os.path.join(
            self.output_dir,
            f"characters_{tutorial_id}.txt"
        )
        self.tutorial_id = tutorial_id

    def extract_characters(self, html_content: str = None) -> List[CharacterData]:
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                print(f"[ERROR] HTML文件不存在: {self.html_path}")
                return []

            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        characters = []

        table_pattern = re.compile(
            r'<tr class="table-row">.*?'
            r'<td[^>]*>.*?<p[^>]*>(\d+)</p>.*?'
            r'<td[^>]*>.*?<p[^>]*>([^<]+)</p>.*?'
            r'</tr>',
            re.DOTALL
        )

        for match in table_pattern.findall(html_content):
            char_id = match[0].strip()
            char_name = match[1].strip()

            if char_id != "对应编号" and char_name != "角色名":
                characters.append(CharacterData(id=char_id, name=char_name))

        if not characters:
            print("[WARN] 使用方法2重新匹配")
            loose_pattern = re.compile(
                r'<td[^>]*>.*?<p[^>]*>(\d{7,})</p>.*?'
                r'<td[^>]*>.*?<p[^>]*>([^<]+)</p>',
                re.DOTALL
            )

            for match in loose_pattern.findall(html_content):
                char_id = match[0].strip()
                char_name = match[1].strip()

                if len(char_id) >= 7:
                    characters.append(CharacterData(id=char_id, name=char_name))

        characters = sorted(set(characters), key=lambda x: int(x.id))

        for idx, char in enumerate(characters, 1):
            char.index = idx

        return characters

    def save_character_data(self, character_data: List[CharacterData]) -> bool:
        if not ErrorHandler.validate_directory_exists(self.output_dir):
            return False

        lines = []
        for char in character_data:
            lines.append(f"{char.index:04d}-{char.id}-{char.name}")

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception as e:
            print(f"[ERROR] 保存角色数据失败: {e}")
            return False


class ChangelogExtractor:
    """从教程更新日志页面提取版本/分类/条目/链接，输出 JSON"""

    CHANGELOG_PATTERN = re.compile(r"更新日志|月之[一二三四五六七八九十]+版本|\d+\.0版本")

    def __init__(self, tutorial_id: str = None):
        if not tutorial_id:
            tutorial_id = "mhs2w008wf14"

        self.tutorial_id = tutorial_id
        self.html_path = os.path.join(
            config_manager.get_output_dir("html"),
            f"tutorial_{tutorial_id}.html"
        )
        self.output_dir = config_manager.get_output_dir("data")
        self.output_path = os.path.join(
            self.output_dir,
            f"changelog_{tutorial_id}.json"
        )
        self.url = f"https://act.mihoyo.com/ys/ugc/tutorial/detail/{tutorial_id}"

    @staticmethod
    def is_changelog(html_content: str) -> bool:
        """检测 HTML 是否为更新日志页面"""
        return bool(ChangelogExtractor.CHANGELOG_PATTERN.search(html_content or ""))

    def extract_all_links(self, html_content: str = None) -> list:
        """从 HTML 中提取所有教程详情页链接，返回 [{title, url, tutorial_id}, ...]"""
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                print(f"[ERROR] HTML文件不存在: {self.html_path}")
                return []
            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        a_pattern = re.compile(
            r'<a[^>]*href="([^"]*tutorial[^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )
        seen_ids = set()
        links = []
        for m in a_pattern.finditer(html_content):
            url = m.group(1).strip()
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if not url or not title:
                continue
            url = re.sub(r'tutorial//detail', 'tutorial/detail', url)
            tid_match = re.search(r'tutorial/detail/([a-z0-9]+)', url)
            if not tid_match:
                continue
            tid = tid_match.group(1)
            if tid in seen_ids or tid == self.tutorial_id:
                continue
            seen_ids.add(tid)
            links.append({"title": title, "url": url, "tutorial_id": tid})
        return links

    def extract(self, html_content: str = None) -> dict:
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                print(f"[ERROR] HTML文件不存在: {self.html_path}")
                return {}
            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        versions = self._parse_versions(html_content)
        result = {
            "page_id": self.tutorial_id,
            "page_title": "更新日志",
            "url": self.url,
            "versions": versions,
        }
        return result

    def _parse_versions(self, html: str) -> list:
        """解析所有版本段"""
        # 匹配 h1/h2 标签中的版本标题，如 "7.0版本-2026/08/12" 或 "月之八版本-2026/07/01"
        version_heading = re.compile(
            r'<h[12][^>]*>\s*([^<]*(?:版本)[^<]*\d{4}/\d{2}/\d{2})\s*</h[12]>',
            re.IGNORECASE
        )
        matches = list(version_heading.finditer(html))
        if not matches:
            print("[WARN] 未找到版本标题")
            return []

        versions = []
        for i, m in enumerate(matches):
            raw_title = m.group(1).strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
            block = html[start:end]

            version, date = self._split_version_date(raw_title)
            categories = self._parse_categories(block)

            versions.append({
                "version": version,
                "date": date,
                "categories": categories,
            })

        return versions

    @staticmethod
    def _split_version_date(raw: str) -> tuple:
        """将 '7.0版本-2026/08/12' 拆分为 ('7.0版本', '2026/08/12')"""
        idx = raw.rfind("-")
        if idx > 0 and re.match(r"\d{4}/\d{2}/\d{2}", raw[idx + 1:]):
            return raw[:idx].strip(), raw[idx + 1:].strip()
        return raw, ""

    def _parse_categories(self, block: str) -> list:
        """解析版本块内的分类（内容新增 / 内容修改）"""
        # 匹配 h2/h3 标签中的分类标题，如 "一、内容新增" 或 "二、内容修改"
        cat_heading = re.compile(
            r'<h[23][^>]*>\s*([^<]*(?:内容新增|内容修改)[^<]*)\s*</h[23]>',
            re.IGNORECASE
        )
        matches = list(cat_heading.finditer(block))
        if not matches:
            return []

        categories = []
        for i, m in enumerate(matches):
            raw_title = m.group(1).strip()
            name = re.sub(r'^[一二三四五六七八九十\d]+、', '', raw_title)
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(block)
            section = block[start:end]

            entries = self._parse_entries(section)
            description = self._extract_description(section)

            categories.append({
                "name": name,
                "description": description,
                "entries": entries,
            })

        return categories

    def _parse_entries(self, section: str) -> list:
        """解析分类区域内的条目（ subsection + 描述 + 链接）"""
        # 匹配 h3/h4 标签中的子标题，如 "1.测距功能"
        sub_heading = re.compile(
            r'<h[34][^>]*>\s*([^<]+)\s*</h[34]>',
            re.IGNORECASE
        )
        sub_matches = list(sub_heading.finditer(section))

        entries = []
        if sub_matches:
            for i, sm in enumerate(sub_matches):
                title = sm.group(1).strip()
                title = re.sub(r'^\d+\.', '', title).strip()
                s_start = sm.end()
                s_end = sub_matches[i + 1].start() if i + 1 < len(sub_matches) else len(section)
                sub_block = section[s_start:s_end]
                desc = self._extract_description(sub_block)
                links = self._extract_links(sub_block)
                entries.append({
                    "title": title,
                    "description": desc,
                    "links": links,
                })
        else:
            # 无子标题的分类，直接提取链接作为条目
            links = self._extract_links(section)
            desc = self._extract_description(section)
            if links:
                entries.append({
                    "title": "",
                    "description": desc,
                    "links": links,
                })

        return entries

    @staticmethod
    def _extract_description(block: str) -> str:
        """提取 <p> 标签中的描述文本"""
        p_pattern = re.compile(r'<p[^>]*>(.*?)</p>', re.DOTALL)
        texts = []
        for m in p_pattern.finditer(block):
            text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
            if text and not text.startswith('更新日志'):
                texts.append(text)
        return "\n".join(texts) if texts else ""

    @staticmethod
    def _extract_links(block: str) -> list:
        """提取 <a> 标签中的链接"""
        a_pattern = re.compile(
            r'<a[^>]*href="([^"]*tutorial[^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )
        links = []
        for m in a_pattern.finditer(block):
            url = m.group(1).strip()
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            if url and title:
                # 修复 URL 中的双斜杠问题
                url = re.sub(r'tutorial//detail', 'tutorial/detail', url)
                links.append({"title": title, "url": url})
        return links

    def save(self, data: dict) -> bool:
        if not ErrorHandler.validate_directory_exists(self.output_dir):
            return False
        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[ERROR] 保存更新日志失败: {e}")
            return False


@handle_errors
def run(tutorial_id: str = None):
    if not tutorial_id:
        tutorial_id = "mh4imrrhzdzi"

    # 读取 HTML 文件
    html_path = os.path.join(
        config_manager.get_output_dir("html"),
        f"tutorial_{tutorial_id}.html"
    )
    if not ErrorHandler.validate_file_exists(html_path):
        print(f"[ERROR] HTML文件不存在: {html_path}")
        print(f"[HINT] 请先执行「抓取米游社教程页面」生成该文件")
        return

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 自动检测页面类型
    if ChangelogExtractor.is_changelog(html_content):
        _run_changelog(tutorial_id, html_content)
    else:
        _run_character_extract(tutorial_id, html_content)


def _run_changelog(tutorial_id: str, html_content: str):
    print("\n[START] 提取更新日志数据")

    extractor = ChangelogExtractor(tutorial_id)
    data = extractor.extract(html_content)

    if not data.get("versions"):
        print("[ERROR] 未找到更新日志数据")
        return

    if extractor.save(data):
        total_entries = sum(
            len(cat.get("entries", []))
            for ver in data["versions"]
            for cat in ver.get("categories", [])
        )
        total_links = sum(
            len(entry.get("links", []))
            for ver in data["versions"]
            for cat in ver.get("categories", [])
            for entry in cat.get("entries", [])
        )
        print(f"[OK] 完成！共 {len(data['versions'])} 个版本，{total_entries} 个条目，{total_links} 个链接")
        print(f"[OK] 已保存到：{extractor.output_path}")

        for ver in data["versions"][:3]:
            print(f"  {ver['version']} ({ver['date']})")
            for cat in ver.get("categories", []):
                entries = cat.get("entries", [])
                print(f"    {cat['name']}: {len(entries)} 个条目")
    else:
        print("[ERROR] 保存更新日志失败")


def _run_character_extract(tutorial_id: str, html_content: str):
    print("\n[START] 提取教程页面角色数据")

    extractor = TutorialExtractor(tutorial_id)
    character_data = extractor.extract_characters(html_content)

    if not character_data:
        print("[ERROR] 未找到角色数据")
        return

    if extractor.save_character_data(character_data):
        print(f"[OK] 完成！共 {len(character_data)} 个角色")
        print(f"[OK] 已保存到：{extractor.output_path}")

        print("\n[INFO] 前5个角色:")
        for char in character_data[:5]:
            print(f"  {char.id} - {char.name}")

        if len(character_data) > 5:
            print(f"  ... 还有 {len(character_data) - 5} 个角色")
    else:
        print("[ERROR] 保存角色数据失败")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        tutorial_id = sys.argv[1]
        run(tutorial_id)
    else:
        run()
