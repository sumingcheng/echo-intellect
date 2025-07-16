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
    """设置并返回一个logger实例"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.handlers = []  # 清除已有处理器
    logger.propagate = True  # 防止日志传播

    formatter = logging.Formatter(format_str)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

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
        except (IOError, PermissionError) as e:
            logger.error(f"无法创建日志文件: {e}")

    return logger
