import unittest
import tempfile
import os
from pathlib import Path


class TestImageExtractor(unittest.TestCase):
    def setUp(self):
        self.test_html = '''
        <div class="collection-avatar__item">
            <img data-src="https://upload-bbs.mihoyo.com/image1.jpg?param=value">
            <div class="collection-avatar__title">角色1</div>
        </div>
        <div class="collection-avatar__item">
            <img data-src="https://upload-bbs.mihoyo.com/image2.png?param=value">
            <div class="collection-avatar__title">角色2</div>
        </div>
        '''
    
    def test_extract_image_urls(self):
        from extractors.images import ImageExtractor

        extractor = ImageExtractor()
        image_data = extractor.extract_image_urls(self.test_html)
        
        self.assertEqual(len(image_data), 2)
        # 注意：ImageExtractor会反转列表顺序
        self.assertEqual(image_data[0].name, "角色2")
        self.assertEqual(image_data[0].url, "https://upload-bbs.mihoyo.com/image2.png")
        self.assertEqual(image_data[1].name, "角色1")
        self.assertEqual(image_data[1].url, "https://upload-bbs.mihoyo.com/image1.jpg")
    
    def test_save_image_data(self):
        from extractors.images import ImageExtractor, ImageData

        extractor = ImageExtractor()
        image_data = [
            ImageData(name="角色1", url="https://upload-bbs.mihoyo.com/image1.jpg", index=1),
            ImageData(name="角色2", url="https://upload-bbs.mihoyo.com/image2.png", index=2)
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            extractor.output_dir = temp_dir
            extractor.output_path = os.path.join(temp_dir, "test_output.txt")
            
            success = extractor.save_image_data(image_data)
            self.assertTrue(success)
            
            with open(extractor.output_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self.assertIn("0001-角色1-[https://upload-bbs.mihoyo.com/image1.jpg]", content)
            self.assertIn("0002-角色2-[https://upload-bbs.mihoyo.com/image2.png]", content)


class TestPostExtractor(unittest.TestCase):
    def setUp(self):
        self.test_html = '''
        <div class="mhy-account-center-post-card">
            <div class="mhy-account-center-time__small">2024-01-15 · 其他信息</div>
            <a href="/ys/article/123"></a>
            <h3 class="mhy-article-card__h3">测试帖子标题</h3>
        </div></div></div>
        '''
    
    def test_extract_posts(self):
        from extractors.time import PostExtractor

        extractor = PostExtractor()
        # 使用不存在的临时路径，避免加载本地真实数据干扰测试
        with tempfile.TemporaryDirectory() as temp_dir:
            extractor.output_path = os.path.join(temp_dir, "nonexistent_posts.txt")
            post_data = extractor.extract_posts(self.test_html)

            self.assertEqual(len(post_data), 1)
            self.assertEqual(post_data[0].title, "测试帖子标题")
            self.assertEqual(post_data[0].date, "2024-01-15")
            self.assertEqual(post_data[0].url, "https://www.miyoushe.com/ys/article/123")
    
    def test_parse_date(self):
        from extractors.time import PostExtractor
        from datetime import datetime
        
        extractor = PostExtractor()
        now = datetime(2024, 1, 20, 12, 0, 0)
        
        # 测试小时前格式
        result = extractor._parse_date("2小时前", now, 2024)
        self.assertEqual(result, "2024-01-20")
        
        # 测试月-日格式
        result = extractor._parse_date("01-15", now, 2024)
        self.assertEqual(result, "2024-01-15")
        
        # 测试完整日期格式
        result = extractor._parse_date("2023-12-25", now, 2024)
        self.assertEqual(result, "2023-12-25")


class TestConfigManager(unittest.TestCase):
    def test_config_loading(self):
        from core.config_manager import ConfigManager
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "test_config.json")
            
            test_config = {
                "user_url": "https://test.example.com",
                "headless": True,
                "wait_seconds": 5
            }
            
            import json
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(test_config, f)
            
            config_manager = ConfigManager(config_path)
            
            self.assertEqual(config_manager.get("user_url"), "https://test.example.com")
            self.assertEqual(config_manager.get("headless"), True)
            self.assertEqual(config_manager.get("wait_seconds"), 5)


if __name__ == '__main__':
    unittest.main()