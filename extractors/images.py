import re
import os
from typing import List
from dataclasses import dataclass
from core.config_manager import config_manager
from utils.error_handler import handle_errors, ErrorHandler


@dataclass
class ImageData:
    name: str
    url: str
    index: int = 0


class ImageExtractor:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.html_path = os.path.join(
            config_manager.get_output_dir("html"),
            config_manager.get_filename("baike_html")
        )
        self.output_dir = config_manager.get_output_dir("images")
        self.output_path = os.path.join(
            self.output_dir,
            config_manager.get_filename("image_urls")
        )

    def extract_image_urls(self, html_content: str = None) -> List[ImageData]:
        if html_content is None:
            if not ErrorHandler.validate_file_exists(self.html_path):
                return []

            with open(self.html_path, "r", encoding="utf-8") as f:
                html_content = f.read()

        pattern = re.compile(
            r'class="collection-avatar__item".*?'
            r'data-src="(https://.*?mihoyo\.com/.*?\.\w+)\?.*?"'
            r'.*?'
            r'class="collection-avatar__title">(.*?)</div>',
            re.DOTALL
        )

        items = []
        for match in pattern.findall(html_content):
            img_url = match[0]
            name = match[1].strip()
            items.append(ImageData(name=name, url=img_url))

        items = list(reversed(items))

        for idx, item in enumerate(items, 1):
            item.index = idx

        return items

    def save_image_data(self, image_data: List[ImageData]) -> bool:
        if not ErrorHandler.validate_directory_exists(self.output_dir):
            return False

        lines = []
        for item in image_data:
            lines.append(f"{item.index:04d}-{item.name}-[{item.url}]")

        try:
            with open(self.output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            return True
        except Exception as e:
            print(f"[ERROR] 保存图片数据失败: {e}")
            return False


@handle_errors
def run():
    print("\n[START] 提取图鉴图片链接")

    extractor = ImageExtractor()
    image_data = extractor.extract_image_urls()

    if not image_data:
        print("[ERROR] 未找到图片数据")
        print(f"[HINT] 请先执行「抓取角色图鉴页面」生成 {extractor.html_path}")
        return

    if extractor.save_image_data(image_data):
        print(f"[OK] 完成！共 {len(image_data)} 个图片链接")
        print(f"[OK] 保存至：{extractor.output_path}")
    else:
        print("[ERROR] 保存图片数据失败")


if __name__ == "__main__":
    run()
