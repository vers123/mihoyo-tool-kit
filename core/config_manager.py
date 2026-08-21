import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

# 平台检测（用于 ZeroTermux 适配）
from utils.platform_detector import get_platform_info


@dataclass
class ZeroTermuxSettings:
    """ZeroTermux / Termux 专属配置"""
    enabled: bool = False              # 是否启用 ZeroTermux 专属适配（环境自动判定为 true 时为 true）
    force_headless: bool = True        # 是否强制 headless 模式（Android 终端无 X Server 默认 true）
    use_mobile_ua: bool = True         # 是否使用移动端 Chrome User-Agent
    enable_low_memory_mode: bool = True  # <4GB 内存时启用：限制 renderer 进程、关闭冗余特性
    extra_browser_args: List[str] = None  # 额外的 Chromium 启动参数（会在基础 browser_args 之后追加）
    scroll_delay_multiplier: float = 1.5  # 移动端滚动延迟放大系数（低端 SoC 渲染较慢）
    timeout_multiplier: float = 1.5       # 移动端网络超时放大系数
    max_backups: int = 5                  # 移动端存储空间偏小，默认减少备份数
    data_dir_override: Optional[str] = None  # 可选：使用 Termux 共享存储区 /sdcard/Download/miHoYo_ToolKit


@dataclass
class OutputDirs:
    html: str = "data/html"
    images: str = "data/images"
    data: str = "data/results"


@dataclass
class Filenames:
    user_html: str = "user_posts.html"
    baike_html: str = "character_list.html"
    image_urls: str = "image_urls.txt"
    posts_data: str = "posts.txt"
    weibo_html: str = "weibo_posts.html"
    weibo_data: str = "weibo.txt"


@dataclass
class ScrollSettings:
    delay: float = 2.0
    max_scroll_attempts: int = 50


@dataclass
class RetrySettings:
    max_attempts: int = 3
    delay: float = 2.0


@dataclass
class IncrementalSettings:
    """增量更新配置"""
    enabled: bool = True  # 是否启用增量更新
    stop_on_existing: bool = True  # 遇到已存在数据时停止滚动
    merge_data: bool = True  # 是否合并新旧数据


@dataclass
class BackupSettings:
    """备份配置"""
    enabled: bool = True  # 是否启用备份
    max_backups: int = 10  # 最大备份数量
    backup_dir: str = "data/backups"  # 备份目录


MOBILE_CHROME_UA = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Mobile Safari/537.36"
)


class ConfigManager:
    """配置管理器，负责配置文件的加载、保存和访问
    适配 ZeroTermux / Termux（Android ARM 环境）：
    1. 动态识别运行环境
    2. 为移动端覆盖 headless / UA / 超时 / 滚动延迟 / browser_args 默认值
    3. 自动追加移动端推荐的 Chromium 参数（swiftshader、静音、关闭音频 OOP 等）
    """

    def __init__(self, config_file: str = "config.json") -> None:
        self.config_file: str = config_file
        self.base_dir: str = os.path.dirname(os.path.dirname(__file__))
        self.config_path: str = os.path.join(self.base_dir, config_file)

        # 先做平台检测（后续用于默认值计算与覆盖层）
        self.platform_info = get_platform_info()
        self.is_zerotermux_env = (
            self.platform_info.is_zerotermux
            or self.platform_info.is_termux
            or self.platform_info.is_android
        )

        self.default_config: Dict[str, Any] = self._get_default_config()
        self.config: Dict[str, Any] = self.default_config.copy()

        self.load_config()
        # 在用户显式配置加载完成后，再应用 ZeroTermux 的弱覆盖（不覆盖用户已设项）
        self._apply_zerotermux_runtime_overrides()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置：基础默认值 + 针对 ZeroTermux 的强默认修正"""
        base_browser_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        zt_extra_args = list(self.platform_info.recommended_extra_browser_args) if self.is_zerotermux_env else []
        merged_browser_args = base_browser_args + zt_extra_args

        default_headless = True if (self.is_zerotermux_env and self.platform_info.recommended_headless) else False
        default_ua = MOBILE_CHROME_UA if (self.is_zerotermux_env and self.platform_info.recommended_headless) else (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        default_timeout = 180000 if self.is_zerotermux_env else 120000
        default_wait_seconds = 5 if self.is_zerotermux_env else 3
        default_scroll_delay = 3.0 if self.is_zerotermux_env else 2.0
        default_retry_max = 5 if self.is_zerotermux_env else 3
        default_retry_delay = 3.0 if self.is_zerotermux_env else 2.0
        default_max_backups = 5 if self.is_zerotermux_env else 10

        defaults = {
            "user_url": "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539",
            "baike_url": "https://baike.mihoyo.com/ys/obc/channel/map/189/25",
            "weibo_url": "https://weibo.com/u/6593199887",
            "headless": default_headless,
            "wait_seconds": default_wait_seconds,
            "timeout": default_timeout,
            "user_agent": default_ua,
            "output_dirs": asdict(OutputDirs()),
            "filenames": asdict(Filenames()),
            "browser_args": merged_browser_args,
            "scroll_settings": {
                "delay": default_scroll_delay,
                "max_scroll_attempts": 50,
            },
            "retry_settings": {
                "max_attempts": default_retry_max,
                "delay": default_retry_delay,
            },
            "incremental_settings": asdict(IncrementalSettings()),
            "backup_settings": {
                "enabled": True,
                "max_backups": default_max_backups,
                "backup_dir": "data/backups",
            },
            "weibo_settings": {
                "use_firefox_cookies": True,
            },
            "miyoushe_settings": {
                "use_firefox_cookies": True,
            },
            "zerotermux_settings": {
                "enabled": self.is_zerotermux_env,
                "force_headless": True,
                "use_mobile_ua": True,
                "enable_low_memory_mode": (0 < self.platform_info.memory_total_mb < 4096) if self.is_zerotermux_env else False,
                "extra_browser_args": zt_extra_args,
                "scroll_delay_multiplier": 1.5,
                "timeout_multiplier": 1.5,
                "max_backups": default_max_backups,
                "data_dir_override": None,
            },
        }
        return defaults

    def _apply_zerotermux_runtime_overrides(self) -> None:
        """ZeroTermux 弱覆盖层：仅对用户未显式写入 config.json 的字段生效。
        用于：移动端首次运行即使默认配置被 JSON 文件覆盖过，也能保证关键的移动端参数就位。"""
        if not self.is_zerotermux_env:
            return

        # 1. headless：若用户没把它改成 true 以外的值，不强制。但若用户写了 false 且无显示器，仍强制改回 true。
        zt = self.config.setdefault("zerotermux_settings", self.default_config["zerotermux_settings"])
        zt_force_headless = bool(zt.get("force_headless", True))
        if zt_force_headless and not self.platform_info.has_display:
            # 终端模式无 X server：headless=false 必定崩溃，强制执行覆盖
            if self.config.get("headless") is not True:
                self.config["headless"] = True

        # 2. UA
        if bool(zt.get("use_mobile_ua", True)):
            current_ua = str(self.config.get("user_agent", ""))
            if "Android" not in current_ua and "Mobile" not in current_ua:
                self.config["user_agent"] = MOBILE_CHROME_UA

        # 3. 备份数量（移动端磁盘较小）
        zt_max_bk = zt.get("max_backups")
        if zt_max_bk is not None:
            backup_settings = self.config.setdefault("backup_settings", {})
            if "max_backups" not in backup_settings:
                backup_settings["max_backups"] = zt_max_bk
            elif backup_settings["max_backups"] > zt_max_bk and self.is_zerotermux_env:
                # 用户配置 > 移动端推荐上限时，降低到上限
                backup_settings["max_backups"] = zt_max_bk

        # 4. 滚动延迟 / 超时 放大系数
        scroll_mult = float(zt.get("scroll_delay_multiplier", 1.0))
        timeout_mult = float(zt.get("timeout_multiplier", 1.0))
        if scroll_mult > 1.0:
            scroll_cfg = self.config.setdefault("scroll_settings", {})
            scroll_cfg["delay"] = round(float(scroll_cfg.get("delay", 2.0)) * scroll_mult, 2)
        if timeout_mult > 1.0:
            self.config["timeout"] = int(int(self.config.get("timeout", 120000)) * timeout_mult)
            self.config["wait_seconds"] = int(int(self.config.get("wait_seconds", 3)) * timeout_mult)

        # 5. browser_args：zerotermux extra + low_memory_mode
        base_args = list(self.config.get("browser_args", []))
        zt_extra = zt.get("extra_browser_args") or []
        for arg in zt_extra:
            if arg not in base_args:
                base_args.append(arg)
        if bool(zt.get("enable_low_memory_mode", False)):
            for arg in (
                "--memory-pressure-off",
                "--renderer-process-limit=1",
                "--in-process-gpu",
            ):
                if arg not in base_args:
                    base_args.append(arg)
        self.config["browser_args"] = base_args

        # 6. data_dir_override：用户指定将输出目录重定向到 Termux 共享存储
        override_dir = zt.get("data_dir_override")
        if override_dir:
            output_dirs = self.config.setdefault("output_dirs", {})
            root = str(override_dir).rstrip("/")
            output_dirs["html"] = f"{root}/html"
            output_dirs["images"] = f"{root}/images"
            output_dirs["data"] = f"{root}/results"
            backup_settings = self.config.setdefault("backup_settings", {})
            backup_settings["backup_dir"] = f"{root}/backups"
    
    def load_config(self) -> None:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    self._deep_update(self.config, user_config)
                print(f"[OK] 已加载配置文件: {self.config_path}")
            except json.JSONDecodeError as e:
                print(f"[WARN] 配置文件格式错误，使用默认配置: {e}")
            except IOError as e:
                print(f"[WARN] 读取配置文件失败，使用默认配置: {e}")
            except Exception as e:
                print(f"[WARN] 加载配置文件时发生未知错误，使用默认配置: {e}")
        else:
            print(f"[INFO] 配置文件不存在，创建默认配置: {self.config_path}")
            self.save_config()
    
    def save_config(self) -> None:
        """保存配置文件"""
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print(f"[OK] 配置文件已保存: {self.config_path}")
        except IOError as e:
            print(f"[ERROR] 保存配置文件失败: {e}")
        except Exception as e:
            print(f"[ERROR] 保存配置文件时发生未知错误: {e}")
    
    def _deep_update(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """深度更新配置字典"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的嵌套路径"""
        keys = key.split('.')
        value: Any = self.config
        try:
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except Exception:
            return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值，支持点号分隔的嵌套路径"""
        keys = key.split('.')
        config = self.config
        try:
            for k in keys[:-1]:
                if k not in config or not isinstance(config[k], dict):
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        except Exception as e:
            print(f"[WARN] 设置配置失败: {e}")
    
    def get_output_dir(self, dir_type: str) -> str:
        """获取输出目录路径"""
        dir_path = self.get(f"output_dirs.{dir_type}")
        if not dir_path:
            dir_path = dir_type
        
        full_path = os.path.join(self.base_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        return full_path
    
    def get_filename(self, file_type: str) -> str:
        """获取文件名"""
        return self.get(f"filenames.{file_type}", "")
    
    def get_scraper_config(self, url: str, output_filename: str) -> Dict[str, Any]:
        """获取抓取器配置"""
        return {
            "url": url,
            "output_filename": output_filename,
            "headless": self.get("headless", False),
            "wait_seconds": self.get("wait_seconds", 3),
            "timeout": self.get("timeout", 120000),
            "user_agent": self.get("user_agent"),
            "browser_args": self.get("browser_args", []),
            "scroll_delay": self.get("scroll_settings.delay", 2.0)
        }


config_manager = ConfigManager()
