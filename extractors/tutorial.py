import re
import os
from typing import List
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


@handle_errors
def run(tutorial_id: str = None):
    print("\n[START] 提取教程页面角色数据")

    if not tutorial_id:
        tutorial_id = "mh4imrrhzdzi"

    extractor = TutorialExtractor(tutorial_id)
    character_data = extractor.extract_characters()

    if not character_data:
        print("[ERROR] 未找到角色数据")
        print(f"[HINT] 请先执行「抓取米游社教程页面」生成 {extractor.html_path}")
        return

    if extractor.save_character_data(character_data):
        print(f"[OK] 完成！共 {len(character_data)} 个角色")
        print(f"[OK] 已保存到：{extractor.output_path}")

        if character_data:
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
