# -*- coding:utf-8 -*-

import datetime
import logging
from logging.handlers import TimedRotatingFileHandler
from ftp_v5.conf.ftp_config import CosFtpConfig


def reformat_lm(last_modified, form="object"):
    if last_modified is None:
        dt_modified = datetime.datetime(1970, 1, 1)
    else:
        try:
            # this is the format used when you use get_all_keys()
            dt_modified = datetime.datetime.strptime(last_modified, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            # this is the format used when you use get_key()
            dt_modified = datetime.datetime.strptime(last_modified, '%a, %d %b %Y %H:%M:%S %Z')
        except:
            raise

    if form == "object":
        return dt_modified
    elif form == "ls":
        if (datetime.datetime.now() - dt_modified).days < 180:
            return dt_modified.strftime("%b %d %H:%M")
        else:
            return dt_modified.strftime("%b %d %Y")
    else:
        return dt_modified.strftime("%Y%m%d%H%M%S")


# 根据配置返回不同的 logger
def get_ftp_logger(module_name):
    # 按照配置的时间滚动
    if CosFtpConfig().log_rotate_enabled:
        size_rotate_handler = TimedRotatingFileHandler(
            backupCount=CosFtpConfig().log_backup_count,
            when = CosFtpConfig().log_rotate_when,
            filename=CosFtpConfig().log_filename
        )
        # 默认输出禁掉
        logging.basicConfig(
            level=CosFtpConfig().log_level,
            format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
            datefmt='%a, %d %b %Y %H:%M:%S',
            filename='/dev/null',
            filemode='w'
        )
        logger = logging.getLogger(module_name)
        formatter = logging.Formatter('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')
        size_rotate_handler.setFormatter(formatter)
        logger.addHandler(size_rotate_handler)
        return logger
    # 默认一直写一个文件
    else:
        logging.basicConfig(
            level=CosFtpConfig().log_level,
            format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
            datefmt='%a, %d %b %Y %H:%M:%S',
            filename=CosFtpConfig().log_filename,
            filemode='w'
        )
        return logging.getLogger(module_name)
