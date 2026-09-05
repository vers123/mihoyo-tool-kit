import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


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


class ConfigManager:
    """配置管理器，负责配置文件的加载、保存和访问"""
    
    def __init__(self, config_file: str = "config.json") -> None:
        self.config_file: str = config_file
        self.base_dir: str = os.path.dirname(os.path.dirname(__file__))
        self.config_path: str = os.path.join(self.base_dir, config_file)
        
        self.default_config: Dict[str, Any] = self._get_default_config()
        self.config: Dict[str, Any] = self.default_config.copy()
        
        self.load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "user_url": "https://www.miyoushe.com/ys/accountCenter/postList?id=75276539",
            "baike_url": "https://baike.mihoyo.com/ys/obc/channel/map/189/25",
            "weibo_url": "https://weibo.com/u/6593199887",
            "headless": False,
            "wait_seconds": 3,
            "timeout": 120000,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "project_root": self.base_dir,
            "output_dirs": asdict(OutputDirs()),
            "filenames": asdict(Filenames()),
            "news_sites": {
                "genshin": {
                    "url": "https://ys.mihoyo.com/main/news",
                    "html_filename": "news_genshin.html",
                    "data_filename": "news_genshin.txt",
                    "scraper_name": "news_genshin",
                    "detail_url_pattern": "/main/news/detail/{iInfoId}",
                    "api_base_url": "https://act-api-takumi-static.mihoyo.com/content_v2_user/app/16471662a82d418a/getContentList",
                    "api_chan_id": "719",
                    "api_page_param": "iPage",
                    "api_page_size_param": "iPageSize",
                    "api_page_size": 5,
                    "api_lang_param": "sLangKey",
                    "api_lang_value": "zh-cn",
                    "fields": ["iInfoId", "sTitle", "dtStartTime", "sCategoryName", "sIntro", "poster_url", "url"],
                    "date_field": "dtStartTime",
                    "poster_ext_key": "720_1",
                    "dir_key": "genshin",
                    "lang_subdir": "zh-cn",
                    "total": 4637
                },
                "genshin_en": {
                    "url": "https://genshin.hoyoverse.com/en/news",
                    "html_filename": "news_genshin_en.html",
                    "data_filename": "news_genshin_en.txt",
                    "scraper_name": "news_genshin_en",
                    "detail_url_pattern": "/en/news/detail/{iInfoId}",
                    "api_base_url": "https://sg-public-api-static.hoyoverse.com/content_v2_user/app/a1b1f9d3315447cc/getContentList",
                    "api_app_id": "32",
                    "api_chan_id": "395",
                    "api_page_param": "iPage",
                    "api_page_size_param": "iPageSize",
                    "api_page_size": 5,
                    "api_lang_param": "sLangKey",
                    "api_lang_value": "en-us",
                    "fields": ["iInfoId", "sTitle", "dtStartTime", "sCategoryName", "sIntro", "poster_url", "url"],
                    "date_field": "dtStartTime",
                    "poster_ext_key": "banner",
                    "dir_key": "genshin",
                    "lang_subdir": "en-us",
                    "total": 2163
                },
                "zzz": {
                    "url": "https://zzz.mihoyo.com/news",
                    "html_filename": "news_zzz.html",
                    "data_filename": "news_zzz.txt",
                    "scraper_name": "news_zzz",
                    "detail_url_pattern": "/news/{iInfoId}",
                    "api_base_url": "https://api-takumi-static.mihoyo.com/content_v2_user/app/706fd13a87294881/getContentList",
                    "api_chan_id": "273",
                    "api_page_param": "iPage",
                    "api_page_size_param": "iPageSize",
                    "api_page_size": 9,
                    "api_lang_param": "sLangKey",
                    "api_lang_value": "zh-cn",
                    "fields": ["iInfoId", "sTitle", "dtStartTime", "sCategoryName", "sIntro", "poster_url", "url"],
                    "date_field": "dtStartTime",
                    "poster_ext_key": "news-banner",
                    "total": 1554
                },
                "starrail": {
                    "url": "https://sr.mihoyo.com/news",
                    "html_filename": "news_starrail.html",
                    "data_filename": "news_starrail.txt",
                    "scraper_name": "news_starrail",
                    "detail_url_pattern": "/news/{iInfoId}",
                    "api_base_url": "https://act-api-takumi-static.mihoyo.com/content_v2_user/app/1963de8dc19e461c/getContentList",
                    "api_chan_id": "255",
                    "api_page_param": "iPage",
                    "api_page_size_param": "iPageSize",
                    "api_page_size": 5,
                    "api_lang_param": "sLangKey",
                    "api_lang_value": "zh-cn",
                    "fields": ["iInfoId", "sTitle", "dtStartTime", "sCategoryName", "sIntro", "poster_url", "url"],
                    "date_field": "dtStartTime",
                    "poster_ext_key": "news-poster",
                    "total": 792
                }
            },
            "migration": {
                "enabled": True,
                "genshin_old_filenames": {
                    "html": "news_page.html",
                    "data": "news.txt"
                }
            },
            "browser_args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            "scroll_settings": asdict(ScrollSettings()),
            "retry_settings": asdict(RetrySettings()),
            "incremental_settings": asdict(IncrementalSettings()),
            "backup_settings": asdict(BackupSettings()),
            "weibo_settings": {
                "use_firefox_cookies": True
            },
            "miyoushe_settings": {
                "use_firefox_cookies": True
            }
        }
    
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
                print(f"[WARN] 加载配置文件时发生未知错误: {e}")
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
    
    def get_project_root(self) -> str:
        """获取项目根目录路径（从配置文件读取，可在 config.json 中覆盖）"""
        return self.get("project_root", self.base_dir)

    def get_output_dir(self, dir_type: str) -> str:
        """获取输出目录路径"""
        dir_path = self.get(f"output_dirs.{dir_type}")
        if not dir_path:
            dir_path = dir_type
        
        full_path = os.path.join(self.base_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        return full_path

    def get_news_output_dir(self, game_key: str, dir_type: str) -> str:
        """获取新闻模块按游戏分子目录的输出路径

        支持 dir_key + lang_subdir 两级子目录，用于同一游戏多语言共存。
        例如 genshin_en 配置 dir_key=genshin, lang_subdir=en-us，
        则输出路径为 data/html/genshin/en-us/

        Args:
            game_key: 游戏标识（genshin / genshin_en / zzz / starrail）
            dir_type: 目录类型（html / data / backup）

        Returns:
            完整的目录路径（如 data/html/genshin/zh-cn/）
        """
        base_dir = self.get_output_dir(dir_type)
        site_config = self.get_news_config(game_key)
        if site_config:
            dir_key = site_config.get("dir_key", game_key)
            lang_subdir = site_config.get("lang_subdir", "")
            game_dir = os.path.join(base_dir, dir_key)
            if lang_subdir:
                game_dir = os.path.join(game_dir, lang_subdir)
        else:
            game_dir = os.path.join(base_dir, game_key)
        os.makedirs(game_dir, exist_ok=True)
        return game_dir

    def get_news_config(self, game_key: str) -> Optional[Dict[str, Any]]:
        """获取指定游戏的新闻配置"""
        return self.get(f"news_sites.{game_key}")

    def get_all_news_sites(self) -> Dict[str, Dict[str, Any]]:
        """获取所有新闻站点配置"""
        return self.get("news_sites", {})
    
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

    def get_news_scraper_config(self, game_key: str) -> Optional[Dict[str, Any]]:
        """获取新闻抓取器配置（整合 news_sites + 通用配置）"""
        site_config = self.get_news_config(game_key)
        if not site_config:
            return None

        html_dir = self.get_news_output_dir(game_key, "html")

        return {
            **site_config,
            "html_dir": html_dir,
            "output_path": os.path.join(html_dir, site_config["html_filename"]),
            "headless": self.get("headless", False),
            "wait_seconds": self.get("wait_seconds", 3),
            "timeout": self.get("timeout", 120000),
            "user_agent": self.get("user_agent"),
            "browser_args": self.get("browser_args", []),
            "scroll_delay": self.get("scroll_settings.delay", 2.0),
        }


config_manager = ConfigManager()
