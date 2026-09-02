#!/usr/bin/env python3
"""
米游社工具箱
基于Playwright的米游社数据抓取和提取工具
支持增量更新和自动备份
"""

import sys
import os
import platform
from typing import Dict, Optional

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

# 导入优化后的模块
from core.config_manager import config_manager
from utils.error_handler import handle_errors
from utils.logger import setup_logger, log_function_call
from utils.backup_manager import backup_manager
from utils.migration import check_and_migrate

# 设置日志
logger = setup_logger("miHoYo_ToolKit")


class MiHoYoToolKit:
    """米游社工具箱主类"""
    
    def __init__(self):
        self.version = "2.2.0"
        self.title = f"米游社工具箱 v{self.version}"
        self.options = self._setup_options()
        
    def _setup_options(self) -> Dict:
        """设置菜单选项（按功能分组）"""
        return {
            # === 米游社用户 ===
            "1": {
                "label": "抓取用户发帖主页",
                "description": "从米游社抓取指定用户的发帖记录",
                "group": "米游社用户",
                "handler": self._fetch_user_posts
            },
            "2": {
                "label": "增量抓取用户发帖",
                "description": "增量更新用户发帖，自动备份旧数据",
                "group": "米游社用户",
                "handler": self._incremental_fetch_user_posts
            },
            "3": {
                "label": "提取用户发帖时间",
                "description": "从用户主页提取发帖时间和标题",
                "group": "米游社用户",
                "handler": self._extract_post_times
            },
            "4": {
                "label": "增量提取用户发帖",
                "description": "增量提取并合并新旧数据",
                "group": "米游社用户",
                "handler": self._incremental_extract_posts
            },
            # === 原神新闻 ===
            "5": {
                "label": "抓取原神新闻页面",
                "description": "从原神官网抓取新闻页面",
                "group": "原神新闻",
                "handler": self._fetch_genshin_news
            },
            "6": {
                "label": "增量抓取原神新闻",
                "description": "增量更新原神新闻，自动备份旧数据",
                "group": "原神新闻",
                "handler": self._incremental_fetch_genshin_news
            },
            "7": {
                "label": "提取原神新闻数据",
                "description": "从新闻页面提取标题、日期、链接等",
                "group": "原神新闻",
                "handler": self._extract_genshin_news
            },
            "8": {
                "label": "增量提取原神新闻",
                "description": "增量提取并合并新旧数据",
                "group": "原神新闻",
                "handler": self._incremental_extract_genshin_news
            },
            # === 绝区零新闻 ===
            "9": {
                "label": "抓取绝区零新闻页面",
                "description": "从绝区零官网抓取新闻页面",
                "group": "绝区零新闻",
                "handler": self._fetch_zzz_news
            },
            "10": {
                "label": "增量抓取绝区零新闻",
                "description": "增量更新绝区零新闻，自动备份旧数据",
                "group": "绝区零新闻",
                "handler": self._incremental_fetch_zzz_news
            },
            "11": {
                "label": "提取绝区零新闻数据",
                "description": "从新闻页面提取标题、日期、链接等",
                "group": "绝区零新闻",
                "handler": self._extract_zzz_news
            },
            "12": {
                "label": "增量提取绝区零新闻",
                "description": "增量提取并合并新旧数据",
                "group": "绝区零新闻",
                "handler": self._incremental_extract_zzz_news
            },
            # === 星穹铁道新闻 ===
            "13": {
                "label": "抓取星穹铁道新闻页面",
                "description": "从星穹铁道官网抓取新闻页面",
                "group": "星穹铁道新闻",
                "handler": self._fetch_starrail_news
            },
            "14": {
                "label": "增量抓取星穹铁道新闻",
                "description": "增量更新星穹铁道新闻，自动备份旧数据",
                "group": "星穹铁道新闻",
                "handler": self._incremental_fetch_starrail_news
            },
            "15": {
                "label": "提取星穹铁道新闻数据",
                "description": "从新闻页面提取标题、日期、链接等",
                "group": "星穹铁道新闻",
                "handler": self._extract_starrail_news
            },
            "16": {
                "label": "增量提取星穹铁道新闻",
                "description": "增量提取并合并新旧数据",
                "group": "星穹铁道新闻",
                "handler": self._incremental_extract_starrail_news
            },
            # === 其他抓取 ===
            "17": {
                "label": "抓取角色图鉴页面",
                "description": "从米游社百科抓取角色图鉴信息",
                "group": "其他抓取",
                "handler": self._fetch_character_baike
            },
            "18": {
                "label": "抓取米游社教程页面",
                "description": "从米游社抓取教程页面",
                "group": "其他抓取",
                "handler": self._fetch_tutorial_page
            },
            "19": {
                "label": "提取教程角色数据",
                "description": "从教程页面提取角色编号和名称",
                "group": "其他抓取",
                "handler": self._extract_tutorial_data
            },
            "20": {
                "label": "提取图鉴图片链接",
                "description": "从抓取的图鉴页面提取角色图片链接",
                "group": "其他抓取",
                "handler": self._extract_image_urls
            },
            "21": {
                "label": "抓取自定义网站",
                "description": "抓取任意网站的HTML页面",
                "group": "其他抓取",
                "handler": self._fetch_custom_site
            },
            # === 微博 ===
            "22": {
                "label": "抓取微博用户主页",
                "description": "从微博抓取指定用户的发帖记录",
                "group": "微博",
                "handler": self._fetch_weibo_posts
            },
            "23": {
                "label": "增量抓取微博用户",
                "description": "增量更新微博用户发帖，自动备份旧数据",
                "group": "微博",
                "handler": self._incremental_fetch_weibo_posts
            },
            "24": {
                "label": "提取微博数据",
                "description": "从微博页面提取发帖时间和内容",
                "group": "微博",
                "handler": self._extract_weibo_data
            },
            "25": {
                "label": "增量提取微博数据",
                "description": "增量提取并合并新旧微博数据",
                "group": "微博",
                "handler": self._incremental_extract_weibo_data
            },
            # === 系统工具 ===
            "26": {
                "label": "查看备份文件",
                "description": "查看所有数据备份文件",
                "group": "系统工具",
                "handler": self._show_backups
            },
            "27": {
                "label": "恢复备份数据",
                "description": "从备份文件恢复数据",
                "group": "系统工具",
                "handler": self._restore_backup
            },
            "28": {
                "label": "查看当前配置",
                "description": "显示当前的配置信息",
                "group": "系统工具",
                "handler": self._show_config
            },
            "29": {
                "label": "修改配置参数",
                "description": "修改URL、超时时间等配置",
                "group": "系统工具",
                "handler": self._modify_config
            },
            "30": {
                "label": "重新加载配置",
                "description": "从配置文件重新加载配置",
                "group": "系统工具",
                "handler": self._reload_config
            },
            "31": {
                "label": "系统信息",
                "description": "显示系统环境和依赖信息",
                "group": "系统工具",
                "handler": self._show_system_info
            },
            "32": {
                "label": "数据迁移工具",
                "description": "迁移旧版本数据到新目录结构",
                "group": "系统工具",
                "handler": self._run_migration
            },
            # === 数据导出 ===
            "33": {
                "label": "导出新闻到 Excel",
                "description": "从 SQLite 导出三游戏新闻到 .xlsx（每游戏一 sheet）",
                "group": "数据导出",
                "handler": self._export_news_excel
            },
            # === 数据导出（D2） ===
            "34": {
                "label": "导出 RSS/JSON Feed",
                "description": "从 SQLite 生成 RSS/JSON feed 供外部订阅",
                "group": "数据导出",
                "handler": self._export_feed
            },
        }
    
    def _clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _print_header(self):
        """打印标题"""
        print("=" * 70)
        print(f"           {self.title}")
        print("=" * 70)
        print("  基于Playwright的米游社数据抓取和提取工具")
        print("=" * 70)
    
    def _print_menu(self):
        """打印菜单（按分组显示）"""
        current_group = None
        for key in sorted(self.options.keys(), key=lambda x: int(x)):
            option = self.options[key]
            group = option.get("group", "")
            
            # 打印分组标题
            if group != current_group:
                if current_group is not None:
                    print()
                print(f"  【{group}】")
                current_group = group
            
            print(f"  {key:>2}. {option['label']}")
            print(f"      {option['description']}")
        
        print("=" * 70)
        print("   0. 退出程序")
        print("=" * 70)
    
    # === 米游社用户 ===
    
    @log_function_call
    @handle_errors
    def _fetch_user_posts(self):
        """抓取用户发帖主页"""
        from fetchers import run_user
        print("\n开始抓取用户发帖主页...")
        run_user(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_user_posts(self):
        """增量抓取用户发帖"""
        from fetchers import run_user
        print("\n开始增量抓取用户发帖...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_user(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_post_times(self):
        """提取用户发帖时间"""
        from extractors import run_extract_time
        print("\n开始提取用户发帖时间...")
        run_extract_time(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_posts(self):
        """增量提取用户发帖"""
        from extractors import run_extract_time
        print("\n开始增量提取用户发帖...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_time(incremental=True)

    # === 原神新闻 ===

    @log_function_call
    @handle_errors
    def _fetch_genshin_news(self):
        """抓取原神新闻页面"""
        from fetchers import run_news_genshin
        print("\n开始抓取原神新闻页面...")
        run_news_genshin(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_genshin_news(self):
        """增量抓取原神新闻"""
        from fetchers import run_news_genshin
        print("\n开始增量抓取原神新闻...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_news_genshin(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_genshin_news(self):
        """提取原神新闻数据"""
        from extractors import run_extract_news_genshin
        print("\n开始提取原神新闻数据...")
        run_extract_news_genshin(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_genshin_news(self):
        """增量提取原神新闻"""
        from extractors import run_extract_news_genshin
        print("\n开始增量提取原神新闻数据...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_news_genshin(incremental=True)

    # === 绝区零新闻 ===

    @log_function_call
    @handle_errors
    def _fetch_zzz_news(self):
        """抓取绝区零新闻页面"""
        from fetchers import run_news_zzz
        print("\n开始抓取绝区零新闻页面...")
        run_news_zzz(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_zzz_news(self):
        """增量抓取绝区零新闻"""
        from fetchers import run_news_zzz
        print("\n开始增量抓取绝区零新闻...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_news_zzz(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_zzz_news(self):
        """提取绝区零新闻数据"""
        from extractors import run_extract_news_zzz
        print("\n开始提取绝区零新闻数据...")
        run_extract_news_zzz(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_zzz_news(self):
        """增量提取绝区零新闻"""
        from extractors import run_extract_news_zzz
        print("\n开始增量提取绝区零新闻数据...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_news_zzz(incremental=True)

    # === 星穹铁道新闻 ===

    @log_function_call
    @handle_errors
    def _fetch_starrail_news(self):
        """抓取星穹铁道新闻页面"""
        from fetchers import run_news_starrail
        print("\n开始抓取星穹铁道新闻页面...")
        run_news_starrail(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_starrail_news(self):
        """增量抓取星穹铁道新闻"""
        from fetchers import run_news_starrail
        print("\n开始增量抓取星穹铁道新闻...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_news_starrail(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_starrail_news(self):
        """提取星穹铁道新闻数据"""
        from extractors import run_extract_news_starrail
        print("\n开始提取星穹铁道新闻数据...")
        run_extract_news_starrail(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_starrail_news(self):
        """增量提取星穹铁道新闻"""
        from extractors import run_extract_news_starrail
        print("\n开始增量提取星穹铁道新闻数据...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_news_starrail(incremental=True)

    # === 其他抓取 ===

    @log_function_call
    @handle_errors
    def _fetch_character_baike(self):
        """抓取角色图鉴页面"""
        from fetchers import run_baike
        print("\n开始抓取角色图鉴页面...")
        run_baike()

    @log_function_call
    @handle_errors
    def _fetch_tutorial_page(self):
        from fetchers import run_tutorial

        print("\n开始抓取米游社教程页面...")
        print("默认教程ID: mh4imrrhzdzi (https://act.mihoyo.com/ys/ugc/tutorial/detail/mh4imrrhzdzi)")

        tutorial_id = input("请输入教程ID [mh4imrrhzdzi]: ").strip()
        if not tutorial_id:
            tutorial_id = "mh4imrrhzdzi"

        print(f"\n[INFO] 开始抓取教程页面: {tutorial_id}")
        print(f"[INFO] 教程链接: https://act.mihoyo.com/ys/ugc/tutorial/detail/{tutorial_id}")

        run_tutorial(tutorial_id)
    
    @log_function_call
    @handle_errors
    def _extract_tutorial_data(self):
        from extractors import run_extract_tutorial

        print("\n开始提取教程页面角色数据...")
        print("默认教程ID: mh4imrrhzdzi")

        tutorial_id = input("请输入教程ID [mh4imrrhzdzi]: ").strip()
        if not tutorial_id:
            tutorial_id = "mh4imrrhzdzi"

        print(f"\n[INFO] 开始提取角色数据: {tutorial_id}")

        run_extract_tutorial(tutorial_id)

    @log_function_call
    @handle_errors
    def _extract_image_urls(self):
        from extractors import run_extract_images
        print("\n开始提取图鉴图片链接...")
        run_extract_images()
    
    @log_function_call
    @handle_errors
    def _fetch_custom_site(self):
        from fetchers import run_custom

        print("\n开始抓取自定义网站...")
        url = input("请输入要抓取的网站URL: ").strip()

        if not url:
            print("[ERROR] URL不能为空")
            return

        filename = input("请输入输出文件名 [custom_page.html]: ").strip()
        if not filename:
            filename = "custom_page.html"

        print(f"\n[INFO] 开始抓取: {url}")
        print(f"[INFO] 输出文件: {filename}")

        run_custom(url, filename)

    # === 微博 ===

    @log_function_call
    @handle_errors
    def _fetch_weibo_posts(self):
        """抓取微博用户主页"""
        from fetchers import run_weibo
        print("\n开始抓取微博用户主页...")
        run_weibo(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_weibo_posts(self):
        """增量抓取微博用户"""
        from fetchers import run_weibo
        print("\n开始增量抓取微博用户...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_weibo(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_weibo_data(self):
        """提取微博数据"""
        from extractors import run_extract_weibo
        print("\n开始提取微博数据...")
        run_extract_weibo(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_weibo_data(self):
        """增量提取微博数据"""
        from extractors import run_extract_weibo
        print("\n开始增量提取微博数据...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_weibo(incremental=True)
    
    # === 系统工具 ===

    def _show_config(self):
        """显示当前配置"""
        print("\n[CONFIG] 当前配置信息：")
        print(f"   用户URL: {config_manager.get('user_url')}")
        print(f"   百科URL: {config_manager.get('baike_url')}")
        print(f"   微博URL: {config_manager.get('weibo_url')}")
        print(f"   无头模式: {config_manager.get('headless')}")
        print(f"   等待时间: {config_manager.get('wait_seconds')}秒")
        print(f"   超时时间: {config_manager.get('timeout')}毫秒")
        print(f"   重试次数: {config_manager.get('retry_settings.max_attempts')}")
        print(f"   增量更新: {config_manager.get('incremental_settings.enabled')}")
        print(f"   备份功能: {config_manager.get('backup_settings.enabled')}")
        print(f"   最大备份数: {config_manager.get('backup_settings.max_backups')}")
        print(f"   配置文件: {config_manager.config_path}")
        print()
        print("   新闻站点：")
        for game_key, site in config_manager.get_all_news_sites().items():
            game_labels = {"genshin": "原神", "zzz": "绝区零", "starrail": "星穹铁道"}
            label = game_labels.get(game_key, game_key)
            print(f"     [{game_key}] {label}: {site['url']} (共{site.get('total', '?')}条)")

    def _show_backups(self):
        """查看备份文件"""
        print("\n[BACKUP] 备份文件列表：")
        print("=" * 70)

        # 显示帖子数据备份
        print("\n帖子数据备份 (posts.txt)：")
        posts_backups = backup_manager.list_backups("posts.txt")
        if posts_backups:
            for i, backup in enumerate(posts_backups, 1):
                size_kb = backup.size / 1024
                print(f"  {i}. {backup.filename}")
                print(f"     创建时间: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     文件大小: {size_kb:.2f} KB")
                print(f"     路径: {backup.filepath}")
        else:
            print("  无备份文件")

        # 显示各游戏新闻数据备份
        game_labels = {"genshin": "原神", "zzz": "绝区零", "starrail": "星穹铁道"}
        for game_key, label in game_labels.items():
            data_filename = config_manager.get(f"news_sites.{game_key}.data_filename", f"news_{game_key}.txt")
            print(f"\n{label}新闻数据备份 ({data_filename})：")
            backups = backup_manager.list_backups(data_filename)
            if backups:
                for i, backup in enumerate(backups, 1):
                    size_kb = backup.size / 1024
                    print(f"  {i}. {backup.filename}")
                    print(f"     创建时间: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"     文件大小: {size_kb:.2f} KB")
                    print(f"     路径: {backup.filepath}")
            else:
                print("  无备份文件")

        # 显示微博数据备份
        print("\n微博数据备份 (weibo.txt)：")
        weibo_backups = backup_manager.list_backups("weibo.txt")
        if weibo_backups:
            for i, backup in enumerate(weibo_backups, 1):
                size_kb = backup.size / 1024
                print(f"  {i}. {backup.filename}")
                print(f"     创建时间: {backup.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"     文件大小: {size_kb:.2f} KB")
                print(f"     路径: {backup.filepath}")
        else:
            print("  无备份文件")

        print("=" * 70)

    def _restore_backup(self):
        """恢复备份数据"""
        print("\n[RESTORE] 恢复备份数据：")
        print(" 1. 恢复帖子数据备份")
        print(" 2. 恢复原神新闻数据备份")
        print(" 3. 恢复绝区零新闻数据备份")
        print(" 4. 恢复星穹铁道新闻数据备份")
        print(" 5. 恢复微博数据备份")
        print(" 0. 返回")

        choice = input("\n请选择操作：").strip()

        if choice == "1":
            self._restore_posts_backup()
        elif choice == "2":
            self._restore_news_backup("genshin", "原神")
        elif choice == "3":
            self._restore_news_backup("zzz", "绝区零")
        elif choice == "4":
            self._restore_news_backup("starrail", "星穹铁道")
        elif choice == "5":
            self._restore_weibo_backup()
        elif choice == "0":
            return
        else:
            print("[ERROR] 无效选项")

    def _restore_posts_backup(self):
        """恢复帖子数据备份"""
        print("\n[RESTORE] 帖子数据备份恢复：")

        backups = backup_manager.list_backups("posts.txt")
        if not backups:
            print("[WARN] 无可用备份文件")
            return

        print("可用的备份文件：")
        for i, backup in enumerate(backups, 1):
            print(f"  {i}. {backup.filename} ({backup.created_at.strftime('%Y-%m-%d %H:%M:%S')})")

        choice = input("\n请选择要恢复的备份序号（输入0返回）：").strip()

        if choice == "0":
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_path = backups[index].filepath
                target_path = os.path.join(
                    config_manager.get_output_dir("data"),
                    "posts.txt"
                )

                if backup_manager.restore_backup(backup_path, target_path):
                    print("[OK] 数据已成功恢复")
                else:
                    print("[ERROR] 数据恢复失败")
            else:
                print("[ERROR] 序号无效")
        except ValueError:
            print("[ERROR] 请输入有效数字")

    def _restore_news_backup(self, game_key: str, game_label: str):
        """恢复新闻数据备份"""
        data_filename = config_manager.get(f"news_sites.{game_key}.data_filename")
        print(f"\n[RESTORE] {game_label}新闻数据备份恢复：")

        backups = backup_manager.list_backups(data_filename)
        if not backups:
            print("[WARN] 无可用备份文件")
            return

        print("可用的备份文件：")
        for i, backup in enumerate(backups, 1):
            print(f"  {i}. {backup.filename} ({backup.created_at.strftime('%Y-%m-%d %H:%M:%S')})")

        choice = input("\n请选择要恢复的备份序号（输入0返回）：").strip()

        if choice == "0":
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_path = backups[index].filepath
                target_path = os.path.join(
                    config_manager.get_news_output_dir(game_key, "data"),
                    data_filename
                )

                if backup_manager.restore_backup(backup_path, target_path):
                    print("[OK] 数据已成功恢复")
                else:
                    print("[ERROR] 数据恢复失败")
            else:
                print("[ERROR] 序号无效")
        except ValueError:
            print("[ERROR] 请输入有效数字")

    def _restore_weibo_backup(self):
        """恢复微博数据备份"""
        print("\n[RESTORE] 微博数据备份恢复：")

        backups = backup_manager.list_backups("weibo.txt")
        if not backups:
            print("[WARN] 无可用备份文件")
            return

        print("可用的备份文件：")
        for i, backup in enumerate(backups, 1):
            print(f"  {i}. {backup.filename} ({backup.created_at.strftime('%Y-%m-%d %H:%M:%S')})")

        choice = input("\n请选择要恢复的备份序号（输入0返回）：").strip()

        if choice == "0":
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup_path = backups[index].filepath
                target_path = os.path.join(
                    config_manager.get_output_dir("data"),
                    "weibo.txt"
                )

                if backup_manager.restore_backup(backup_path, target_path):
                    print("[OK] 数据已成功恢复")
                else:
                    print("[ERROR] 数据恢复失败")
            else:
                print("[ERROR] 序号无效")
        except ValueError:
            print("[ERROR] 请输入有效数字")
    
    def _modify_config(self):
        """修改配置参数"""
        print("\n[SETTINGS] 配置修改（直接回车保持原值）")
        
        # 用户URL
        current_url = config_manager.get("user_url")
        new_url = input(f"用户URL [{current_url}]: ").strip()
        if new_url:
            config_manager.set("user_url", new_url)
        
        # 百科URL
        current_baike = config_manager.get("baike_url")
        new_baike = input(f"百科URL [{current_baike}]: ").strip()
        if new_baike:
            config_manager.set("baike_url", new_baike)
        
        # 微博URL
        current_weibo = config_manager.get("weibo_url")
        new_weibo = input(f"微博URL [{current_weibo}]: ").strip()
        if new_weibo:
            config_manager.set("weibo_url", new_weibo)
        
        # 等待时间
        current_wait = config_manager.get("wait_seconds")
        new_wait = input(f"等待时间(秒) [{current_wait}]: ").strip()
        if new_wait and new_wait.isdigit():
            config_manager.set("wait_seconds", int(new_wait))
        
        # 保存配置
        config_manager.save_config()
        print("[OK] 配置已保存")
    
    def _reload_config(self):
        """重新加载配置"""
        config_manager.load_config()
        print("[OK] 配置已重新加载")
    
    def _show_system_info(self):
        """显示系统信息"""
        print("\n[SYSTEM] 系统信息：")
        print(f"   操作系统: {platform.system()} {platform.release()}")
        print(f"   Python版本: {platform.python_version()}")
        print(f"   工作目录: {os.path.dirname(__file__)}")
        print(f"   配置文件: {config_manager.config_path}")
        print(f"   版本号: {self.version}")
        
        # 检查Playwright
        try:
            import playwright
            from playwright._repo_version import version
            print(f"   Playwright版本: {version}")
        except ImportError:
            print("   Playwright: 未安装")
        except Exception as e:
            print(f"   Playwright版本: 无法获取 ({e})")

    def _run_migration(self):
        """运行数据迁移工具"""
        from utils.migration import DataMigrationManager

        print("\n[MIGRATION] 数据迁移工具")
        print("=" * 70)
        print("将旧版本数据文件迁移到新的目录结构和命名规范")
        print()

        manager = DataMigrationManager()

        if not manager.needs_migration():
            print("[INFO] 当前不需要数据迁移")
            print("所有数据文件已经是最新的目录结构和命名规范")
            return

        print("检测到以下文件需要迁移：")
        for old_path, new_path in manager._get_genshin_old_files():
            if os.path.exists(old_path):
                print(f"  - {os.path.basename(old_path)} → {os.path.basename(new_path)}")

        print()
        confirm = input("确认执行数据迁移吗？(y/N): ").strip().lower()

        if confirm == "y":
            result = manager.run_migration()
            if result["success"]:
                print(f"\n[OK] 数据迁移成功完成！")
                print(f"   迁移文件数: {len(result['migrated_files'])}")
                print(f"   跳过文件数: {len(result['skipped_files'])}")
                print("\n[提示] 源文件已保留，确认无误后可手动删除")
            else:
                print(f"\n[ERROR] 数据迁移出现错误")
                for err in result["errors"]:
                    print(f"   - {err}")
        else:
            print("[INFO] 已取消迁移")

    def _export_news_excel(self):
        """导出三游戏新闻到 Excel（从 SQLite 读取，每游戏一 sheet）"""
        from extractors import run_export_excel

        print("\n[EXPORT] 导出新闻到 Excel")
        print("=" * 70)
        print("从 SQLite 读取三游戏新闻，写入 .xlsx（每游戏一 sheet）")
        print()

        try:
            path = run_export_excel()
        except Exception as e:
            print(f"\n[ERROR] 导出失败: {e}")
            logger.error(f"Excel 导出失败: {e}", exc_info=True)
            return

        # 展示各游戏条数
        try:
            from core.storage import NewsStorage

            with NewsStorage() as store:
                counts = store.count_all()
            print("\n各游戏条数：")
            for game, n in counts.items():
                print(f"   {game}: {n} 条")
        except Exception:
            pass

    def _export_feed(self):
        """导出 RSS/JSON Feed（从 SQLite 读取，供外部订阅）"""
        from core.feed import generate_json_feed, generate_rss_feed

        print("\n[FEED] 导出 RSS/JSON Feed")
        print("=" * 70)
        print("1) RSS 2.0  -> output/news_feed.xml")
        print("2) JSON Feed -> output/news_feed.json")
        choice = input("\n选择格式 (1/2，默认 1)：").strip() or "1"
        try:
            if choice == "2":
                generate_json_feed()
            else:
                generate_rss_feed()
        except Exception as e:
            print(f"\n[ERROR] 导出失败: {e}")
            logger.error(f"Feed 导出失败: {e}", exc_info=True)

    def run(self):
        """运行主程序"""
        logger.info("米游社工具箱启动")
        
        while True:
            self._clear_screen()
            self._print_header()
            self._print_menu()
            
            choice = input("\n请输入序号：").strip()
            
            if choice == "0":
                print("\n感谢使用米游社工具箱，再见！")
                logger.info("米游社工具箱退出")
                sys.exit(0)
            
            if choice in self.options:
                try:
                    self.options[choice]["handler"]()
                    input("\n按回车键继续...")
                except KeyboardInterrupt:
                    print("\n\n操作已取消")
                    input("按回车键继续...")
                except Exception as e:
                    logger.error(f"执行出错: {e}", exc_info=True)
                    print(f"\n[ERROR] 执行出错: {e}")
                    input("按回车键继续...")
            else:
                print("[ERROR] 无效的选择，请重新输入")
                input("按回车键继续...")


@handle_errors
def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="米游社工具箱")
    parser.add_argument("--gui", action="store_true", help="启动 GUI 图形界面")
    args = parser.parse_args()

    print("[START] 正在初始化米游社工具箱...")

    # 检查依赖
    try:
        import playwright
        print("[OK] Playwright依赖检查通过")
    except ImportError:
        print("[ERROR] 缺少Playwright依赖，请运行: pip install playwright")
        print("然后运行: playwright install chromium")
        return

    # 检查并执行数据迁移（自动）
    try:
        check_and_migrate()
    except Exception as e:
        print(f"[WARN] 数据迁移检查失败: {e}")

    if args.gui:
        from gui import launch_gui
        launch_gui()
    else:
        toolkit = MiHoYoToolKit()
        toolkit.run()


if __name__ == "__main__":
    main()
