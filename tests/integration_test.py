"""
集成测试脚本 - 验证项目整体结构和功能
运行方式: python tests/integration_test.py
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print('=' * 60)
print('集成测试：项目整体验证')
print('=' * 60)

# 1. 核心模块
print('\n[1/7] 核心模块导入:')
from core.config_manager import config_manager
print('  - config_manager: OK')

# 2. 提取器模块
print('\n[2/7] 提取器模块导入:')
from extractors.news.base import GameNewsBaseExtractor, NewsItem
from extractors.news.genshin import GenshinNewsExtractor
from extractors.news.genshin_en import GenshinENNewsExtractor
from extractors.news.zzz import ZZZNewsExtractor
from extractors.news.starrail import SRNewsExtractor
print('  - GameNewsBaseExtractor: OK')
print('  - GenshinNewsExtractor: OK')
print('  - GenshinENNewsExtractor: OK')
print('  - ZZZNewsExtractor: OK')
print('  - SRNewsExtractor: OK')

# 3. 配置验证
print('\n[3/7] 配置验证:')
all_sites = config_manager.get_all_news_sites()
assert len(all_sites) == 4, f'期望4个站点，实际{len(all_sites)}个'
print(f'  - 新闻站点数量: {len(all_sites)}')

expected_sites = {
    'genshin': {'chan_id': '719', 'total': 4637},
    'genshin_en': {'chan_id': '395', 'total': 2163},
    'zzz': {'chan_id': '273', 'total': 1554},
    'starrail': {'chan_id': '255', 'total': 792},
}

for key, expected in expected_sites.items():
    site = all_sites[key]
    assert site['api_chan_id'] == expected['chan_id'], f'{key} chan_id 不匹配'
    assert site['total'] == expected['total'], f'{key} total 不匹配'
    assert 'api_base_url' in site, f'{key} 缺少 api_base_url'
    assert 'html_filename' in site, f'{key} 缺少 html_filename'
    assert 'data_filename' in site, f'{key} 缺少 data_filename'
    print(f'  - {key}: OK (iChanId={site["api_chan_id"]}, 总数={site["total"]})')

# 4. 输出目录验证
print('\n[4/7] 输出目录验证:')
for game_key in ['genshin', 'genshin_en', 'zzz', 'starrail']:
    html_dir = config_manager.get_news_output_dir(game_key, 'html')
    data_dir = config_manager.get_news_output_dir(game_key, 'data')
    assert os.path.isdir(html_dir), f'{game_key} html 目录不存在'
    assert os.path.isdir(data_dir), f'{game_key} data 目录不存在'
    print(f'  - {game_key}: OK')

# 5. 端到端提取测试
print('\n[5/7] 端到端提取测试:')
test_html = '''
<!DOCTYPE html>
<html lang="zh-cn">
<head><meta charset="utf-8"><title>测试</title></head>
<body>
<div class="news-container">
<ul class="news__list">
<li class="news__item" data-id="1001">
    <div class="news__poster"><img src="https://example.com/p1.jpg" alt="封面"></div>
    <div class="news__content">
        <span class="news__category">公告</span>
        <a href="/news/1001" class="news__title">
            <h3 title="第一条新闻标题">第一条新闻标题</h3>
        </a>
        <p class="news__intro">新闻摘要内容</p>
        <div class="news__date">2024-01-15 10:00:00</div>
    </div>
</li>
<li class="news__item" data-id="1002">
    <div class="news__content">
        <span class="news__category">活动</span>
        <a href="/news/1002" class="news__title">
            <h3 title="第二条新闻">第二条新闻</h3>
        </a>
        <div class="news__date">2024-01-14</div>
    </div>
</li>
</ul>
</div>
</body>
</html>
'''

# 测试四个站点的提取器
for name, ExtClass in [
    ('原神', GenshinNewsExtractor),
    ('原神(EN)', GenshinENNewsExtractor),
    ('绝区零', ZZZNewsExtractor),
    ('星穹铁道', SRNewsExtractor),
]:
    ext = ExtClass()
    items = ext._parse_html(test_html)
    assert len(items) == 2, f'{name}提取器期望2条，实际{len(items)}条'

    item0 = items[0]
    assert item0.iInfoId == '1001', f'{name} iInfoId 不匹配'
    assert item0.title == '第一条新闻标题', f'{name} title 不匹配'
    assert item0.category == '公告', f'{name} category 不匹配'
    assert item0.intro == '新闻摘要内容', f'{name} intro 不匹配'
    assert item0.poster_url == 'https://example.com/p1.jpg', f'{name} poster 不匹配'
    assert item0.date == '2024-01-15 10:00:00', f'{name} date 不匹配'
    assert '/news/1001' in item0.url, f'{name} url 不匹配'

    item1 = items[1]
    assert item1.iInfoId == '1002'
    assert item1.category == '活动'
    assert item1.intro == ''
    assert item1.poster_url == ''

    print(f'  - {name}提取器: OK (2条新闻，7字段完整)')

# 6. 数据保存与加载测试
print('\n[6/7] 数据保存与加载测试:')
ext = GenshinNewsExtractor()
items = ext._parse_html(test_html)
for i, item in enumerate(items, 1):
    item.index = i

with tempfile.TemporaryDirectory() as temp_dir:
    ext.data_dir = temp_dir
    ext.output_path = os.path.join(temp_dir, "test_news.txt")

    # 保存
    success = ext.save_news_data(items)
    assert success, '保存失败'
    assert os.path.exists(ext.output_path), '输出文件不存在'
    print('  - 保存数据: OK')

    # 加载（新格式）
    loaded = ext.load_existing_data()
    assert len(loaded) == 2, f'加载期望2条，实际{len(loaded)}条'
    assert loaded[0].title == '第一条新闻标题'
    assert loaded[0].category == '公告'
    assert loaded[0].intro == '新闻摘要内容'
    assert loaded[0].poster_url == 'https://example.com/p1.jpg'
    print('  - 加载新格式: OK')

    # 测试旧格式兼容
    old_format_path = os.path.join(temp_dir, "old_format.txt")
    with open(old_format_path, "w", encoding="utf-8") as f:
        f.write("0001-旧新闻标题-[2024-01-01]-(https://example.com/old/1)\n")
        f.write("0002-旧新闻标题2-[2024-01-02]-(https://example.com/old/2)\n")

    ext.output_path = old_format_path
    old_loaded = ext.load_existing_data()
    assert len(old_loaded) == 2, f'旧格式加载期望2条，实际{len(old_loaded)}条'
    assert old_loaded[0].title == '旧新闻标题'
    assert old_loaded[0].category == ''  # 旧格式无分类
    assert old_loaded[0].intro == ''  # 旧格式无摘要
    print('  - 旧格式兼容: OK')

# 7. 数据迁移工具
print('\n[7/7] 数据迁移工具:')
from utils.migration import DataMigrationManager
mgr = DataMigrationManager()
assert hasattr(mgr, 'needs_migration')
assert hasattr(mgr, 'run_migration')
assert hasattr(mgr, 'rollback_migration')
print('  - DataMigrationManager: OK')
print(f'  - 需要迁移: {mgr.needs_migration()}')

print('\n' + '=' * 60)
print('集成测试全部通过！')
print('=' * 60)
