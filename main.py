#!/usr/bin/env python3
"""
米游社工具箱
基于Playwright的米游社数据抓取和提取工具
支持增量更新和自动备份
适配平台：Windows / macOS / Linux / ZeroTermux(Termux/Android)
"""

import sys
import os
import platform as _platform_mod
from typing import Dict, Optional

# 添加项目路径
sys.path.append(os.path.dirname(__file__))

# 导入优化后的模块
from core.config_manager import config_manager
from utils.error_handler import handle_errors
from utils.logger import setup_logger, log_function_call
from utils.backup_manager import backup_manager
from utils.platform_detector import get_platform_info, PlatformInfo

# 设置日志
logger = setup_logger("miHoYo_ToolKit")


class MiHoYoToolKit:
    """米游社工具箱主类
    ZeroTermux 适配：
      - 启动时检测运行环境，显示 ZeroTermux 专属 banner
      - 清屏命令兼容 Android 终端（TERM=screen 或 tmux）
      - 系统信息展示补充 ZeroTermux 版本、proot 容器名、内存信息等
      - 依赖检查对 ZeroTermux 给出 proot-distro 安装指引
    """

    MIN_PYTHON_VERSION = (3, 8)

    def __init__(self):
        self.version = "2.1.0"
        self.platform_info: PlatformInfo = get_platform_info()
        # 附加版本标签：ZeroTermux 模式
        mode_tag = ""
        if self.platform_info.is_zerotermux:
            mode_tag = " (ZeroTermux模式)"
        elif self.platform_info.is_termux:
            mode_tag = " (Termux模式)"
        elif self.platform_info.is_android:
            mode_tag = " (Android模式)"
        self.title = f"米游社工具箱 v{self.version}{mode_tag}"
        self.options = self._setup_options()
        
    def _setup_options(self) -> Dict:
        """设置菜单选项"""
        return {
            "1": {
                "label": "抓取用户发帖主页",
                "description": "从米游社抓取指定用户的发帖记录",
                "handler": self._fetch_user_posts
            },
            "2": {
                "label": "增量抓取用户发帖",
                "description": "增量更新用户发帖，自动备份旧数据",
                "handler": self._incremental_fetch_user_posts
            },
            "3": {
                "label": "抓取角色图鉴页面",
                "description": "从米游社百科抓取角色图鉴信息",
                "handler": self._fetch_character_baike
            },
            "4": {
                "label": "抓取原神新闻页面",
                "description": "从原神官网抓取新闻页面",
                "handler": self._fetch_genshin_news
            },
            "5": {
                "label": "增量抓取原神新闻",
                "description": "增量更新原神新闻，自动备份旧数据",
                "handler": self._incremental_fetch_news
            },
            "6": {
                "label": "抓取米游社教程页面",
                "description": "从米游社抓取教程页面",
                "handler": self._fetch_tutorial_page
            },
            "7": {
                "label": "提取教程角色数据",
                "description": "从教程页面提取角色编号和名称",
                "handler": self._extract_tutorial_data
            },
            "8": {
                "label": "抓取自定义网站",
                "description": "抓取任意网站的HTML页面",
                "handler": self._fetch_custom_site
            },
            "9": {
                "label": "提取图鉴图片链接",
                "description": "从抓取的图鉴页面提取角色图片链接",
                "handler": self._extract_image_urls
            },
            "10": {
                "label": "提取用户发帖时间",
                "description": "从用户主页提取发帖时间和标题",
                "handler": self._extract_post_times
            },
            "11": {
                "label": "增量提取用户发帖",
                "description": "增量提取并合并新旧数据",
                "handler": self._incremental_extract_posts
            },
            "12": {
                "label": "提取原神新闻数据",
                "description": "从新闻页面提取标题和链接",
                "handler": self._extract_news_data
            },
            "13": {
                "label": "增量提取新闻数据",
                "description": "增量提取并合并新旧数据",
                "handler": self._incremental_extract_news
            },
            "14": {
                "label": "抓取微博用户主页",
                "description": "从微博抓取指定用户的发帖记录",
                "handler": self._fetch_weibo_posts
            },
            "15": {
                "label": "增量抓取微博用户",
                "description": "增量更新微博用户发帖，自动备份旧数据",
                "handler": self._incremental_fetch_weibo_posts
            },
            "16": {
                "label": "提取微博数据",
                "description": "从微博页面提取发帖时间和内容",
                "handler": self._extract_weibo_data
            },
            "17": {
                "label": "增量提取微博数据",
                "description": "增量提取并合并新旧微博数据",
                "handler": self._incremental_extract_weibo_data
            },
            "18": {
                "label": "查看备份文件",
                "description": "查看所有数据备份文件",
                "handler": self._show_backups
            },
            "19": {
                "label": "恢复备份数据",
                "description": "从备份文件恢复数据",
                "handler": self._restore_backup
            },
            "20": {
                "label": "查看当前配置",
                "description": "显示当前的配置信息",
                "handler": self._show_config
            },
            "21": {
                "label": "修改配置参数",
                "description": "修改URL、超时时间等配置",
                "handler": self._modify_config
            },
            "22": {
                "label": "重新加载配置",
                "description": "从配置文件重新加载配置",
                "handler": self._reload_config
            },
            "23": {
                "label": "系统信息",
                "description": "显示系统环境和依赖信息",
                "handler": self._show_system_info
            }
        }
    
    def _clear_screen(self):
        """清屏，兼容 Windows / POSIX / 窄终端（ZeroTermux 小屏幕）
        优先尝试 ANSI escape，其次系统 shell 命令，失败则打印 40 空行兜底"""
        try:
            # ANSI ESC: 光标移原点 + 清屏到末尾
            sys.stdout.write("\033[H\033[2J\033[3J")
            sys.stdout.flush()
            return
        except Exception:
            pass
        try:
            if os.name == "nt":
                os.system("cls")
            else:
                term = os.environ.get("TERM", "")
                if term in ("dumb", ""):
                    # 无 TERM 的情况下打印空行兜底
                    print("\n" * 40)
                else:
                    os.system("clear")
        except Exception:
            print("\n" * 40)

    def _zerotermux_banner_line(self) -> Optional[str]:
        """生成移动端专属 banner 文字（在标题下方展示，便于用户一眼看到运行模式状态）"""
        info = self.platform_info
        if not info.needs_mobile_optimized_browser:
            return None
        parts = []
        if info.is_zerotermux:
            ver = info.zerotermux_version or "0.118.3.64"
            parts.append(f"ZeroTermux {ver}")
        elif info.is_termux:
            parts.append("Termux")
        if info.is_proot_distro and info.proot_distro_name:
            parts.append(f"proot({info.proot_distro_name})")
        parts.append(f"arch={info.arch}")
        if info.memory_total_mb > 0:
            parts.append(f"RAM≈{info.memory_total_mb}MB")
        parts.append(f"headless={'YES' if config_manager.get('headless') else 'NO'}")
        return "  📱 " + "  |  ".join(parts)

    def _print_header(self):
        """打印标题，窄终端自动缩短分隔线宽度"""
        # 估算终端宽度（ZeroTermux 默认竖屏常 80 列以下）
        try:
            terminal_cols, _ = os.get_terminal_size()
        except Exception:
            terminal_cols = 70
        banner_width = max(48, min(70, terminal_cols - 2))

        print("=" * banner_width)
        # 标题居中或靠左（窄屏靠左更合适）
        if terminal_cols >= 60:
            print(f"           {self.title}")
        else:
            print(f" {self.title}")
        print("=" * banner_width)
        zt_line = self._zerotermux_banner_line()
        if zt_line:
            print(zt_line)
        print("  基于Playwright的米游社数据抓取和提取工具")
        print("=" * banner_width)
    
    def _print_menu(self):
        """打印菜单"""
        for key in sorted(self.options.keys(), key=int):
            option = self.options[key]
            print(f"  {key}. {option['label']}")
            print(f"      {option['description']}")
        
        print("=" * 70)
        print("  0. 退出程序")
        print("=" * 70)
    
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
    def _fetch_character_baike(self):
        """抓取角色图鉴页面"""
        from fetchers import run_baike
        print("\n开始抓取角色图鉴页面...")
        run_baike()

    @log_function_call
    @handle_errors
    def _fetch_genshin_news(self):
        """抓取原神新闻页面"""
        from fetchers import run_news
        print("\n开始抓取原神新闻页面...")
        run_news(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_fetch_news(self):
        """增量抓取原神新闻"""
        from fetchers import run_news
        print("\n开始增量抓取原神新闻...")
        print("[INFO] 增量模式: 自动备份旧数据，遇到已存在数据停止抓取")
        run_news(incremental=True)

    @log_function_call
    @handle_errors
    def _extract_image_urls(self):
        from extractors import run_extract_images
        print("\n开始提取图鉴图片链接...")
        run_extract_images()

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

    @log_function_call
    @handle_errors
    def _extract_news_data(self):
        """提取原神新闻数据"""
        from extractors import run_extract_news
        print("\n开始提取原神新闻数据...")
        run_extract_news(incremental=False)

    @log_function_call
    @handle_errors
    def _incremental_extract_news(self):
        """增量提取新闻数据"""
        from extractors import run_extract_news
        print("\n开始增量提取新闻数据...")
        print("[INFO] 增量模式: 自动备份旧数据，合并新旧数据")
        run_extract_news(incremental=True)
    
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

        # 显示新闻数据备份
        print("\n新闻数据备份 (news.txt)：")
        news_backups = backup_manager.list_backups("news.txt")
        if news_backups:
            for i, backup in enumerate(news_backups, 1):
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
        print("1. 恢复帖子数据备份")
        print("2. 恢复新闻数据备份")
        print("3. 恢复微博数据备份")
        print("0. 返回")

        choice = input("\n请选择操作：").strip()

        if choice == "1":
            self._restore_posts_backup()
        elif choice == "2":
            self._restore_news_backup()
        elif choice == "3":
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

    def _restore_news_backup(self):
        """恢复新闻数据备份"""
        print("\n[RESTORE] 新闻数据备份恢复：")

        backups = backup_manager.list_backups("news.txt")
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
                    "news.txt"
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
        info = self.platform_info
        print("\n[SYSTEM] 系统信息：")
        print(f"   操作系统: {_platform_mod.system()} {_platform_mod.release()}")
        print(f"   Python版本: {_platform_mod.python_version()}")
        print(f"   工作目录: {os.path.dirname(__file__)}")
        print(f"   配置文件: {config_manager.config_path}")
        print(f"   CPU架构: {info.arch}")
        if info.is_zerotermux:
            ver = info.zerotermux_version or "0.118.3.64"
            print(f"   ✅ ZeroTermux版本: {ver}")
        if info.is_termux and info.termux_prefix:
            print(f"   Termux PREFIX: {info.termux_prefix}")
        if info.is_proot_distro:
            name = info.proot_distro_name or "unknown"
            print(f"   proot-distro容器: {name}")
        if info.memory_total_mb > 0:
            print(f"   系统内存: 约 {info.memory_total_mb} MB" + (
                "  （<4GB 已启用低内存模式）" if info.memory_total_mb < 4096 else ""
            ))
        if info.has_display:
            print(f"   显示服务: YES ($DISPLAY=$DISPLAY)".replace("$DISPLAY", os.environ.get("DISPLAY", "") or os.environ.get("WAYLAND_DISPLAY", "")))
        else:
            print("   显示服务: NO  （将以 headless 模式启动浏览器）")
        if info.needs_mobile_optimized_browser:
            # 打印当前生效的 zerotermux 配置摘要
            zt_cfg = config_manager.get("zerotermux_settings", {}) or {}
            print(f"   移动端适配: 启用")
            print(f"      · force_headless    = {zt_cfg.get('force_headless', True)}")
            print(f"      · use_mobile_ua     = {zt_cfg.get('use_mobile_ua', True)}")
            print(f"      · low_memory_mode   = {zt_cfg.get('enable_low_memory_mode', False)}")
            m = zt_cfg.get('scroll_delay_multiplier', 1.0)
            t = zt_cfg.get('timeout_multiplier', 1.0)
            print(f"      · scroll × {m} / timeout × {t}")
            # 提示 chromium 可执行路径
            from core.scraper import _locate_chromium_executable
            p = _locate_chromium_executable()
            if p:
                print(f"      · Chromium 路径: {p}")
            else:
                print("      · Chromium 路径: 未自动检测（运行 scripts/install_zerotermux.sh 或设置 MIHOYO_TOOLKIT_CHROMIUM_BIN）")

        # 检查Playwright
        try:
            import playwright  # noqa: F401
            from playwright._repo_version import version
            print(f"   Playwright版本: {version}")
        except ImportError:
            print("   Playwright: 未安装")
        except Exception as e:
            print(f"   Playwright版本: 无法获取 ({e})")

    def run(self):
        """运行主程序"""
        logger.info("米游社工具箱启动")
        # ZeroTermux 模式启动时输出一次环境提示（写入日志文件）
        if self.platform_info.needs_mobile_optimized_browser:
            zt_cfg = config_manager.get("zerotermux_settings", {}) or {}
            logger.info(
                f"移动端适配已启用: "
                f"zerotermux={self.platform_info.is_zerotermux}, "
                f"termux={self.platform_info.is_termux}, "
                f"proot={self.platform_info.is_proot_distro}, "
                f"arch={self.platform_info.arch}, "
                f"headless={config_manager.get('headless')}, "
                f"mobile_ua={zt_cfg.get('use_mobile_ua', True)}"
            )

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
    # 1. Python 版本前置检查（playwright 要求 3.8+，ZeroTermux/Python 3.11 常见）
    py_ver = sys.version_info[:2]
    if py_ver < MiHoYoToolKit.MIN_PYTHON_VERSION:
        required = ".".join(str(x) for x in MiHoYoToolKit.MIN_PYTHON_VERSION)
        actual = ".".join(str(x) for x in py_ver)
        print(f"[FATAL] Python 版本过旧：需要 {required}+，当前 {actual}")
        print("        ZeroTermux 中请运行: pkg install python")
        return

    print("[START] 正在初始化米游社工具箱...")
    info = get_platform_info()
    if info.is_zerotermux:
        print("[INFO] 检测到 ZeroTermux 运行环境，已自动启用移动端适配方案（headless/mobile-UA/低内存优化）")
    elif info.is_termux:
        print("[INFO] 检测到 Termux 运行环境，已自动启用移动端适配方案")
    elif info.is_android:
        print("[INFO] 检测到 Android 环境，已自动启用移动端适配方案")

    # 2. 依赖检查（ZeroTermux 下引导使用 proot-distro 安装 chromium）
    try:
        import playwright  # noqa: F401
        print("[OK] Playwright依赖检查通过")
    except ImportError:
        print("[ERROR] 缺少Playwright依赖。")
        if info.needs_mobile_optimized_browser:
            print("       请在 ZeroTermux 中依次执行：")
            print("       $  pkg install git python python-pip proot-distro")
            print("       $  cd miHoYo_ToolKit")
            print("       $  pip install -r requirements.txt")
            print("       $  bash scripts/install_zerotermux.sh  # 自动安装 proot-distro + chromium")
        else:
            print("       请运行: pip install playwright && playwright install chromium")
        return

    # 启动工具箱
    toolkit = MiHoYoToolKit()
    toolkit.run()


if __name__ == "__main__":
    main()