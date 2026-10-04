import functools
import time
import logging
from typing import Callable, Any, Tuple, Type


def handle_errors(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except FileNotFoundError as e:
            logging.error(f"文件未找到错误: {e}")
            print(f"❌ 错误：文件未找到 - {e}")
            return None
        except ConnectionError as e:
            logging.error(f"网络连接错误: {e}")
            print(f"❌ 错误：网络连接失败 - {e}")
            return None
        except TimeoutError as e:
            logging.error(f"请求超时错误: {e}")
            print(f"❌ 错误：请求超时 - {e}")
            return None
        except Exception as e:
            logging.error(f"未知错误: {e}", exc_info=True)
            print(f"❌ 发生未知错误: {e}")
            return None
    return wrapper


def retry(max_attempts: int = 3, delay: float = 2.0, exceptions: Tuple[Type[Exception], ...] = (Exception,)) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    print(f"⚠️ 第{attempt + 1}次尝试失败，{delay}秒后重试...")
                    time.sleep(delay)

            if last_exception:
                logging.error(f"所有{max_attempts}次尝试均失败: {last_exception}")
                print(f"❌ 所有{max_attempts}次尝试均失败")
                raise last_exception

            return None
        return wrapper
    return decorator


class ErrorHandler:
    @staticmethod
    def safe_execute(func: Callable, *args, default_return=None, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"安全执行失败: {e}", exc_info=True)
            return default_return

    @staticmethod
    def validate_file_exists(filepath: str) -> bool:
        import os
        if not os.path.exists(filepath):
            logging.warning(f"文件不存在: {filepath}")
            print(f"[WARN] 文件不存在: {filepath}")
            return False
        return True

    @staticmethod
    def validate_directory_exists(dirpath: str) -> bool:
        import os
        if not os.path.exists(dirpath):
            try:
                os.makedirs(dirpath, exist_ok=True)
                print(f"📁 创建目录: {dirpath}")
                return True
            except Exception as e:
                logging.error(f"创建目录失败: {dirpath} - {e}")
                print(f"❌ 创建目录失败: {dirpath}")
                return False
        return True
