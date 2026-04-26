import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logger(
    name,
    log_file=None,
    level=logging.INFO,
    format_str="%(asctime)s - %(name)s - %(levelname)s - %(pathname)s:%(funcName)s:%(lineno)d - %(message)s",
    max_bytes=10 * 1024 * 1024,
    backup_count=5,
    encoding="utf-8",
):
    """设置并返回一个logger实例，同时配置 root logger。"""
    formatter = logging.Formatter(format_str)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置 root logger，确保所有 getLogger() 调用者都有输出
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(level)
        root.addHandler(console_handler)

    # 配置命名 logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []
    logger.propagate = True

    if log_file:
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding=encoding,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            root.addHandler(file_handler)
        except (IOError, PermissionError) as e:
            logger.error(f"无法创建日志文件: {e}")

    return logger
