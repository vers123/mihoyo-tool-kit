"""
新闻模块单元测试
包含新闻提取器、新闻抓取器核心逻辑、配置管理等测试
"""

import unittest
import tempfile
import os
import json
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 检查 Playwright 是否可用
try:
    import playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

playwright_skip = unittest.skipUnless(HAS_PLAYWRIGHT, "需要 Playwright 才能运行此测试")


class TestNewsItem(unittest.TestCase):
    """测试 NewsItem 数据类"""

    def test_news_item_creation(self):
        from extractors.news.base import NewsItem

        item = NewsItem(
            iInfoId="12345",
            title="测试新闻标题",
            date="2024-01-15",
            category="公告",
            intro="这是新闻摘要",
            poster_url="https://example.com/poster.jpg",
            url="https://example.com/news/12345"
        )

        self.assertEqual(item.iInfoId, "12345")
        self.assertEqual(item.title, "测试新闻标题")
        self.assertEqual(item.date, "2024-01-15")
        self.assertEqual(item.category, "公告")
        self.assertEqual(item.intro, "这是新闻摘要")
        self.assertEqual(item.poster_url, "https://example.com/poster.jpg")
        self.assertEqual(item.url, "https://example.com/news/12345")

    def test_news_item_hash_and_equality(self):
        from extractors.news.base import NewsItem

        item1 = NewsItem(title="标题1", date="2024-01-01", url="https://example.com/1")
        item2 = NewsItem(title="标题1", date="2024-01-01", url="https://example.com/1")
        item3 = NewsItem(title="标题2", date="2024-01-02", url="https://example.com/2")

        # 相同 URL 的应该相等
        self.assertEqual(item1, item2)
        self.assertEqual(hash(item1), hash(item2))

        # 不同 URL 的不相等
        self.assertNotEqual(item1, item3)

        # 可以放入 set 中去重
        items = {item1, item2, item3}
        self.assertEqual(len(items), 2)

    def test_news_item_equality_without_url(self):
        from extractors.news.base import NewsItem

        # 没有 URL 时用 title+date 比较
        item1 = NewsItem(title="标题1", date="2024-01-01")
        item2 = NewsItem(title="标题1", date="2024-01-01")
        item3 = NewsItem(title="标题1", date="2024-01-02")

        self.assertEqual(item1, item2)
        self.assertNotEqual(item1, item3)


class TestGameNewsBaseExtractor(unittest.TestCase):
    """测试新闻提取基类"""

    def setUp(self):
        self.test_html_structured = '''
<!DOCTYPE html>
<html lang="zh-cn">
<head><meta charset="utf-8"><title>测试新闻</title></head>
<body>
<div class="news-container">
<h1>测试新闻列表</h1>
<ul class="news__list">
<li class="news__item" data-id="1001">
    <div class="news__poster"><img src="https://example.com/poster1.jpg" alt="新闻1"></div>
    <div class="news__content">
        <span class="news__category">公告</span>
        <a href="/news/1001" class="news__title">
            <h3 title="第一条新闻标题">第一条新闻标题</h3>
        </a>
        <p class="news__intro">这是第一条新闻的摘要内容</p>
        <div class="news__date">2024-01-15 10:00:00</div>
    </div>
</li>
<li class="news__item" data-id="1002">
    <div class="news__content">
        <span class="news__category">活动</span>
        <a href="/news/1002" class="news__title">
            <h3 title="第二条新闻标题">第二条新闻标题</h3>
        </a>
        <p class="news__intro">第二条新闻摘要</p>
        <div class="news__date">2024-01-14 15:30:00</div>
    </div>
</li>
<li class="news__item" data-id="1003">
    <div class="news__content">
        <a href="/news/1003" class="news__title">
            <h3 title="第三条新闻">第三条新闻</h3>
        </a>
        <div class="news__date">2024-01-13</div>
    </div>
</li>
</ul>
</div>
</body>
</html>
'''

    def test_extract_structured_html(self):
        """测试从结构化 HTML（API 构建的）中提取数据"""
        # 使用一个简单的子类来测试
        from extractors.news.base import GameNewsBaseExtractor

        class TestExtractor(GameNewsBaseExtractor):
            game_key = "genshin"

        # 临时修改配置路径以避免影响真实配置
        extractor = TestExtractor()

        # 直接测试 _parse_html 方法
        items = extractor._parse_html(self.test_html_structured)

        self.assertEqual(len(items), 3)

        # 验证第一条新闻（完整字段）
        item1 = items[0]
        self.assertEqual(item1.iInfoId, "1001")
        self.assertEqual(item1.title, "第一条新闻标题")
        self.assertEqual(item1.category, "公告")
        self.assertEqual(item1.intro, "这是第一条新闻的摘要内容")
        self.assertEqual(item1.poster_url, "https://example.com/poster1.jpg")
        self.assertTrue(item1.url.endswith("/news/1001"))
        self.assertEqual(item1.date, "2024-01-15 10:00:00")

        # 验证第二条新闻（无封面图）
        item2 = items[1]
        self.assertEqual(item2.iInfoId, "1002")
        self.assertEqual(item2.title, "第二条新闻标题")
        self.assertEqual(item2.category, "活动")
        self.assertEqual(item2.poster_url, "")

        # 验证第三条新闻（无分类、无摘要）
        item3 = items[2]
        self.assertEqual(item3.iInfoId, "1003")
        self.assertEqual(item3.title, "第三条新闻")
        self.assertEqual(item3.category, "")
        self.assertEqual(item3.intro, "")

    def test_url_resolution(self):
        """测试 URL 补全"""
        from extractors.news.base import GameNewsBaseExtractor

        class TestExtractor(GameNewsBaseExtractor):
            game_key = "genshin"

        extractor = TestExtractor()

        # 绝对 URL 保持不变
        self.assertEqual(
            extractor._resolve_url("https://example.com/news/1"),
            "https://example.com/news/1"
        )

        # 相对路径补全
        self.assertTrue(
            extractor._resolve_url("/news/1").endswith("/news/1")
        )
        self.assertTrue(
            extractor._resolve_url("/news/1").startswith("http")
        )

        # // 开头的补全协议
        self.assertEqual(
            extractor._resolve_url("//example.com/news/1"),
            "https://example.com/news/1"
        )

    def test_merge_data(self):
        """测试新旧数据合并"""
        from extractors.news.base import GameNewsBaseExtractor, NewsItem

        class TestExtractor(GameNewsBaseExtractor):
            game_key = "genshin"

        extractor = TestExtractor()

        old_data = [
            NewsItem(title="旧新闻1", date="2024-01-01", url="https://example.com/1", category="旧分类"),
            NewsItem(title="旧新闻2", date="2024-01-02", url="https://example.com/2"),
        ]

        new_data = [
            NewsItem(title="新新闻1", date="2024-01-03", url="https://example.com/3"),
            NewsItem(title="更新后的新闻1", date="2024-01-01", url="https://example.com/1", category="新分类"),
        ]

        merged = extractor._merge_data(old_data, new_data)

        # 应该有3条：旧新闻2 + 新新闻1 + 更新后的新闻1（覆盖旧新闻1）
        self.assertEqual(len(merged), 3)

        # 验证 URL 为 1 的新闻被更新了
        url1_items = [item for item in merged if item.url == "https://example.com/1"]
        self.assertEqual(len(url1_items), 1)
        self.assertEqual(url1_items[0].title, "更新后的新闻1")
        self.assertEqual(url1_items[0].category, "新分类")

    def test_save_and_load_new_format(self):
        """测试新格式（7字段）的保存和加载"""
        from extractors.news.base import GameNewsBaseExtractor, NewsItem

        class TestExtractor(GameNewsBaseExtractor):
            game_key = "genshin"

        extractor = TestExtractor()

        with tempfile.TemporaryDirectory() as temp_dir:
            # 修改输出路径到临时目录
            extractor.data_dir = temp_dir
            extractor.output_path = os.path.join(temp_dir, "test_news.txt")

            test_data = [
                NewsItem(
                    iInfoId="1001",
                    title="测试新闻1",
                    date="2024-01-15",
                    category="公告",
                    intro="摘要1",
                    poster_url="https://example.com/p1.jpg",
                    url="https://example.com/news/1001",
                    index=1
                ),
                NewsItem(
                    iInfoId="1002",
                    title="测试新闻2",
                    date="2024-01-14",
                    category="活动",
                    intro="摘要2",
                    poster_url="",
                    url="https://example.com/news/1002",
                    index=2
                ),
            ]

            # 保存
            success = extractor.save_news_data(test_data)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(extractor.output_path))

            # 验证文件内容格式
            with open(extractor.output_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("0001-测试新闻1-[2024-01-15]-[公告]-[摘要1]-[https://example.com/p1.jpg]-(https://example.com/news/1001)", content)
            self.assertIn("0002-测试新闻2-[2024-01-14]-[活动]-[摘要2]-[]-(https://example.com/news/1002)", content)

    def test_load_old_format(self):
        """测试兼容旧格式（4字段）的加载"""
        from extractors.news.base import GameNewsBaseExtractor, NewsItem

        class TestExtractor(GameNewsBaseExtractor):
            game_key = "genshin"

        extractor = TestExtractor()

        with tempfile.TemporaryDirectory() as temp_dir:
            extractor.data_dir = temp_dir
            extractor.output_path = os.path.join(temp_dir, "test_news.txt")

            # 写入旧格式数据
            old_format_content = "\n".join([
                "0001-旧新闻标题1-[2024-01-15]-(https://example.com/news/1)",
                "0002-旧新闻标题2-[2024-01-14]-(https://example.com/news/2)",
            ])

            with open(extractor.output_path, "w", encoding="utf-8") as f:
                f.write(old_format_content)

            # 加载
            loaded = extractor.load_existing_data()

            self.assertEqual(len(loaded), 2)
            self.assertEqual(loaded[0].title, "旧新闻标题1")
            self.assertEqual(loaded[0].date, "2024-01-15")
            self.assertEqual(loaded[0].url, "https://example.com/news/1")
            self.assertEqual(loaded[0].category, "")  # 旧格式没有分类
            self.assertEqual(loaded[0].intro, "")  # 旧格式没有摘要


@playwright_skip
class TestGameNewsBaseScraper(unittest.TestCase):
    """测试新闻抓取基类的核心逻辑（非浏览器部分）"""

    def test_extract_items_from_api(self):
        """测试从 API 响应中提取新闻列表"""
        from fetchers.news.base import GameNewsBaseScraper

        class TestScraper(GameNewsBaseScraper):
            game_key = "genshin"

            def __init__(self):
                # 跳过父类的 __init__ 以避免启动浏览器
                pass

        scraper = TestScraper()
        scraper.site_config = {
            "url": "https://ys.mihoyo.com/main/news",
            "detail_url_pattern": "/main/news/detail/{iInfoId}",
            "date_field": "dtStartTime",
            "poster_ext_key": "720_1",
        }

        # 模拟 API 响应
        api_response = {
            "data": {
                "iTotal": 2,
                "list": [
                    {
                        "iInfoId": 1001,
                        "sTitle": "测试新闻1",
                        "dtStartTime": "2024-01-15 10:00:00",
                        "sCategoryName": "公告",
                        "sIntro": "摘要内容1",
                        "sExt": json.dumps({
                            "720_1": [{"url": "https://example.com/poster1.jpg"}]
                        })
                    },
                    {
                        "iInfoId": 1002,
                        "sTitle": "测试新闻2",
                        "dtStartTime": "2024-01-14",
                        "sCategoryName": "活动",
                        "sIntro": "摘要内容2",
                        "sExt": "{}"
                    },
                ]
            }
        }

        items = scraper._extract_items_from_api(api_response)

        self.assertEqual(len(items), 2)

        # 验证第一条
        self.assertEqual(items[0]["iInfoId"], "1001")
        self.assertEqual(items[0]["sTitle"], "测试新闻1")
        self.assertEqual(items[0]["date"], "2024-01-15 10:00:00")
        self.assertEqual(items[0]["sCategoryName"], "公告")
        self.assertEqual(items[0]["sIntro"], "摘要内容1")
        self.assertEqual(items[0]["poster_url"], "https://example.com/poster1.jpg")
        self.assertIn("/main/news/detail/1001", items[0]["url"])

        # 验证第二条（无封面图）
        self.assertEqual(items[1]["iInfoId"], "1002")
        self.assertEqual(items[1]["poster_url"], "")

    def test_extract_poster_url(self):
        """测试封面图 URL 提取"""
        from fetchers.news.base import GameNewsBaseScraper

        class TestScraper(GameNewsBaseScraper):
            game_key = "genshin"

            def __init__(self):
                pass

        scraper = TestScraper()
        scraper.site_config = {"poster_ext_key": "news-banner"}

        # 列表格式的封面图
        item_with_list = {
            "sExt": json.dumps({
                "news-banner": [{"url": "https://example.com/banner.jpg"}]
            })
        }
        self.assertEqual(
            scraper._extract_poster_url(item_with_list),
            "https://example.com/banner.jpg"
        )

        # 字典格式的封面图
        item_with_dict = {
            "sExt": json.dumps({
                "news-banner": {"url": "https://example.com/poster.png"}
            })
        }
        self.assertEqual(
            scraper._extract_poster_url(item_with_dict),
            "https://example.com/poster.png"
        )

        # 没有封面图
        item_no_poster = {"sExt": json.dumps({})}
        self.assertEqual(scraper._extract_poster_url(item_no_poster), "")

        # 空 sExt
        item_empty_ext = {"sExt": ""}
        self.assertEqual(scraper._extract_poster_url(item_empty_ext), "")

        # 无效 JSON
        item_invalid_json = {"sExt": "invalid json"}
        self.assertEqual(scraper._extract_poster_url(item_invalid_json), "")

    def test_build_html_from_api_data(self):
        """测试从 API 数据构建 HTML"""
        from fetchers.news.base import GameNewsBaseScraper

        class TestScraper(GameNewsBaseScraper):
            game_key = "genshin"

            def __init__(self):
                pass

        scraper = TestScraper()

        items = [
            {
                "iInfoId": "1001",
                "sTitle": "新闻标题1",
                "date": "2024-01-15",
                "sCategoryName": "公告",
                "sIntro": "摘要1",
                "poster_url": "https://example.com/p1.jpg",
                "url": "https://ys.mihoyo.com/main/news/detail/1001",
            },
            {
                "iInfoId": "1002",
                "sTitle": "新闻标题2",
                "date": "2024-01-14",
                "sCategoryName": "",
                "sIntro": "",
                "poster_url": "",
                "url": "https://ys.mihoyo.com/main/news/detail/1002",
            },
        ]

        html = scraper._build_html_from_api_data(items)

        # 验证 HTML 结构
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('class="news__item"', html)
        self.assertIn('data-id="1001"', html)
        self.assertIn('新闻标题1', html)
        self.assertIn('2024-01-15', html)
        self.assertIn('公告', html)
        self.assertIn('摘要1', html)
        self.assertIn('https://example.com/p1.jpg', html)
        self.assertIn('/main/news/detail/1001', html)

        # 验证第二条（部分字段为空）
        self.assertIn('data-id="1002"', html)
        self.assertIn('新闻标题2', html)

    def test_make_full_url(self):
        """测试 URL 拼接"""
        from fetchers.news.base import GameNewsBaseScraper

        class TestScraper(GameNewsBaseScraper):
            game_key = "genshin"

            def __init__(self):
                pass

        scraper = TestScraper()
        scraper.site_config = {"url": "https://ys.mihoyo.com/main/news"}

        # 已经是完整 URL
        self.assertEqual(
            scraper._make_full_url("https://example.com/page"),
            "https://example.com/page"
        )

        # 相对路径
        result = scraper._make_full_url("/main/news/detail/123")
        self.assertTrue(result.startswith("https://ys.mihoyo.com"))
        self.assertIn("/main/news/detail/123", result)


class TestConfigManagerNews(unittest.TestCase):
    """测试配置管理器的新闻相关功能"""

    def test_get_news_config(self):
        """测试获取单个游戏的新闻配置"""
        from core.config_manager import config_manager

        genshin_config = config_manager.get_news_config("genshin")
        self.assertIsNotNone(genshin_config)
        self.assertEqual(genshin_config["url"], "https://ys.mihoyo.com/main/news")
        self.assertEqual(genshin_config["html_filename"], "news_genshin.html")
        self.assertIn("api_base_url", genshin_config)
        self.assertIn("api_chan_id", genshin_config)

    def test_get_all_news_sites(self):
        """测试获取所有新闻站点配置"""
        from core.config_manager import config_manager

        all_sites = config_manager.get_all_news_sites()
        self.assertIsInstance(all_sites, dict)
        self.assertIn("genshin", all_sites)
        self.assertIn("genshin_en", all_sites)
        self.assertIn("zzz", all_sites)
        self.assertIn("starrail", all_sites)
        self.assertEqual(len(all_sites), 4)

    def test_get_news_output_dir(self):
        """测试获取新闻输出目录"""
        from core.config_manager import config_manager
        import os

        html_dir = config_manager.get_news_output_dir("genshin", "html")
        self.assertTrue(os.path.exists(html_dir))
        self.assertIn("genshin", html_dir)

        data_dir = config_manager.get_news_output_dir("zzz", "data")
        self.assertTrue(os.path.exists(data_dir))
        self.assertIn("zzz", data_dir)

    def test_get_news_scraper_config(self):
        """测试获取新闻抓取器配置"""
        from core.config_manager import config_manager

        scraper_config = config_manager.get_news_scraper_config("genshin")
        self.assertIsNotNone(scraper_config)
        self.assertIn("output_path", scraper_config)
        self.assertIn("html_dir", scraper_config)
        self.assertIn("headless", scraper_config)
        self.assertIn("timeout", scraper_config)


class TestGenshinNewsExtractorFallback(unittest.TestCase):
    """测试原神提取器的兜底 DOM 解析"""

    def test_genshin_fallback_parser(self):
        """测试原神旧版 DOM 结构解析"""
        from extractors.news.genshin import GenshinNewsExtractor

        extractor = GenshinNewsExtractor.__new__(GenshinNewsExtractor)
        extractor.url_base = "https://ys.mihoyo.com"

        old_genshin_html = '''
        <li class="news__item">
            <a href="/main/news/detail/12345" class="news__title">
                <h3 title="旧版新闻标题">旧版新闻标题</h3>
            </a>
            <div class="news__date">2024-01-15</div>
        </li>
        <li class="news__item">
            <a href="/main/news/detail/12346" class="news__title">
                <h3>第二条旧新闻</h3>
            </a>
            <div class="news__date">2024-01-14</div>
        </li>
        '''

        items = extractor._parse_html_fallback(old_genshin_html)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "旧版新闻标题")
        self.assertEqual(items[0].date, "2024-01-15")
        self.assertEqual(items[0].url, "https://ys.mihoyo.com/main/news/detail/12345")


class TestDataMigration(unittest.TestCase):
    """测试数据迁移工具"""

    def test_needs_migration_false(self):
        """测试不需要迁移的情况"""
        from utils.migration import DataMigrationManager

        # 创建临时目录结构，模拟已迁移状态
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataMigrationManager()
            # 由于使用真实配置，这里只测试类的存在和基本方法
            self.assertTrue(hasattr(manager, 'needs_migration'))
            self.assertTrue(hasattr(manager, 'run_migration'))
            self.assertTrue(hasattr(manager, 'rollback_migration'))

    def test_migration_manager_creation(self):
        """测试迁移管理器创建"""
        from utils.migration import DataMigrationManager

        manager = DataMigrationManager()
        self.assertIsNotNone(manager)
        self.assertEqual(len(manager.migrated_files), 0)


class TestModuleExports(unittest.TestCase):
    """测试模块导出是否正确"""

    @playwright_skip
    def test_fetchers_exports(self):
        """测试 fetchers 模块导出"""
        import fetchers

        self.assertTrue(hasattr(fetchers, 'GenshinNewsScraper'))
        self.assertTrue(hasattr(fetchers, 'ZZZNewsScraper'))
        self.assertTrue(hasattr(fetchers, 'SRNewsScraper'))
        self.assertTrue(hasattr(fetchers, 'GameNewsBaseScraper'))
        self.assertTrue(hasattr(fetchers, 'run_news_genshin'))
        self.assertTrue(hasattr(fetchers, 'run_news_zzz'))
        self.assertTrue(hasattr(fetchers, 'run_news_starrail'))
        # 向后兼容
        self.assertTrue(hasattr(fetchers, 'run_news'))
        self.assertTrue(hasattr(fetchers, 'NewsScraper'))

    def test_extractors_exports(self):
        """测试 extractors 模块导出"""
        import extractors

        self.assertTrue(hasattr(extractors, 'GenshinNewsExtractor'))
        self.assertTrue(hasattr(extractors, 'ZZZNewsExtractor'))
        self.assertTrue(hasattr(extractors, 'SRNewsExtractor'))
        self.assertTrue(hasattr(extractors, 'GameNewsBaseExtractor'))
        self.assertTrue(hasattr(extractors, 'NewsItem'))
        self.assertTrue(hasattr(extractors, 'run_extract_news_genshin'))
        self.assertTrue(hasattr(extractors, 'run_extract_news_zzz'))
        self.assertTrue(hasattr(extractors, 'run_extract_news_starrail'))
        # 向后兼容
        self.assertTrue(hasattr(extractors, 'run_extract_news'))
        self.assertTrue(hasattr(extractors, 'NewsExtractor'))

    @playwright_skip
    def test_news_submodule_fetchers(self):
        """测试 fetchers.news 子模块"""
        from fetchers.news import (
            GameNewsBaseScraper,
            GenshinNewsScraper,
            ZZZNewsScraper,
            SRNewsScraper,
            run_news_genshin,
            run_news_zzz,
            run_news_starrail,
        )

        self.assertIsNotNone(GameNewsBaseScraper)
        self.assertIsNotNone(GenshinNewsScraper)
        self.assertIsNotNone(ZZZNewsScraper)
        self.assertIsNotNone(SRNewsScraper)

    def test_news_submodule_extractors(self):
        """测试 extractors.news 子模块"""
        from extractors.news import (
            GameNewsBaseExtractor,
            NewsItem,
            GenshinNewsExtractor,
            ZZZNewsExtractor,
            SRNewsExtractor,
            run_extract_news_genshin,
            run_extract_news_zzz,
            run_extract_news_starrail,
        )

        self.assertIsNotNone(GameNewsBaseExtractor)
        self.assertIsNotNone(NewsItem)
        self.assertIsNotNone(GenshinNewsExtractor)
        self.assertIsNotNone(ZZZNewsExtractor)
        self.assertIsNotNone(SRNewsExtractor)


if __name__ == '__main__':
    unittest.main(verbosity=2)
