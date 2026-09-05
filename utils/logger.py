import logging
import sys
import functools
from pathlib import Path
from typing import Optional


class LoggerConfig:
    def __init__(self, log_level: str = "INFO", log_file: str = "app.log"):
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_file = log_file


def setup_logger(name: str, config: Optional[LoggerConfig] = None) -> logging.Logger:
    """设置统一的日志系统"""
    if config is None:
        config = LoggerConfig()
    
    logger = logging.getLogger(name)
    logger.setLevel(config.log_level)
    
    if logger.handlers:
        return logger
    
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / config.log_file
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(config.log_level)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_module_logger(module_name: str) -> logging.Logger:
    """为模块获取预配置的logger"""
    return setup_logger(module_name)


def log_function_call(func):
    """记录函数调用的装饰器"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_module_logger(func.__module__)
        logger.info(f"调用函数: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}", exc_info=True)
            raise

    return wrapper
