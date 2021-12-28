# -*- coding:utf-8 -*-

import ConfigParser
import logging
import math
import os
import platform
import threading
from multiprocessing import cpu_count

import ftp_v5.conf.common_config
from ftp_v5 import system_info


class CosFtpConfig(object):
    CONFIG_PATH = None
    if platform.system() == "Windows":
        CONFIG_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) + \
                      "\\conf\\vsftpd.conf.example"
    else:
        CONFIG_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) + \
                      "/conf/vsftpd.conf"

    @classmethod
    def _check_ipv4(cls, ipv4):
        if len(ipv4.split(".")) != 4:
            return False
        for value in ipv4.split("."):
            try:
                value = int(value)
                if value < 0 or value > 255:
                    return False
            except ValueError:
                return False

        return True

    _instance = None
    _isInit = False
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CosFtpConfig, cls).__new__(cls)
            return cls._instance

    def __init__(self):
        if CosFtpConfig._isInit:
            return

        cfg = ConfigParser.RawConfigParser()
        cfg.read(CosFtpConfig.CONFIG_PATH)

        sections = cfg.sections()  # 获取所有的sections

        self.all_COS_UserInfo_Map = dict()
        self.login_users = list()
        for section in sections:
            if str(section).startswith("COS_ACCOUNT"):
                user_info = dict()
                user_info['cos_secretid'] = cfg.get(section, "cos_secretid")
                user_info['cos_secretkey'] = cfg.get(section, "cos_secretkey")
                cos_v5_bucket = cfg.get(section, 'cos_bucket')
                if len(cos_v5_bucket) < 2:
                    raise ValueError("Config error: bucket option must be {bucket name}-{appid} in section:" + section)
                try:
                    user_info['bucket'] = cos_v5_bucket
                    user_info['appid'] = str(cos_v5_bucket).split('-')[-1]
                except TypeError:
                    raise ValueError("Config error: bucket failed must be {bucket name}-{appid} in section:" + section)
                except ValueError:
                    raise ValueError("Config error: bucket failed must be {bucket name}-{appid} in section:" + section)

                user_info['cos_protocol'] = "https"

                if cfg.has_option(section, 'cos_protocol'):
                    user_info['cos_protocol'] = cfg.get(section, 'cos_protocol')

                user_info['cos_region'] = str()
                user_info['cos_endpoint'] = str()
                if cfg.has_option(section, "cos_region"):
                    user_info['cos_region'] = cfg.get(section, "cos_region")

                if cfg.has_option(section, "cos_endpoint"):
                    user_info['cos_endpoint'] = cfg.get(section, "cos_endpoint")

                if cfg.has_option(section, "delete_enable"):
                    user_info['delete_enable'] = cfg.getboolean(section, "delete_enable")
                else:
                    user_info['delete_enable'] = True

                home_dir = cfg.get(section, "home_dir")
                if str(home_dir).endswith("/"):
                    home_dir = str(home_dir)[:-1]

                login_username = cfg.get(section, "ftp_login_user_name")
                login_password = cfg.get(section, "ftp_login_user_password")
                authority = cfg.get(section, "authority")
                self.login_users.append((login_username, login_password, home_dir, authority))
                self.all_COS_UserInfo_Map[home_dir] = user_info

        self.masquerade_address = None
        if cfg.has_section("NETWORK") and cfg.has_option("NETWORK", "masquerade_address") and str(
                cfg.get("NETWORK", "masquerade_address")) != "":
            if CosFtpConfig._check_ipv4(cfg.get("NETWORK", "masquerade_address")):
                self.masquerade_address = cfg.get("NETWORK", "masquerade_address")
        else:
            self.masquerade_address = None

        self.listen_port = int(cfg.get("NETWORK", "listen_port"))
        passive_ports = cfg.get("NETWORK", 'passive_port').split(',')
        if len(passive_ports) > 1:
            self.passive_ports = range(int(passive_ports[0]), int(passive_ports[1]))
        elif len(passive_ports) == 1:
            self.passive_ports = range(int(passive_ports[0]), 65535)
        else:
            self.passive_ports = range(60000, 65535)

        if cfg.has_section("FILE_OPTION") and cfg.has_option("FILE_OPTION", "single_file_max_size"):
            self.single_file_max_size = int(cfg.get("FILE_OPTION", "single_file_max_size"))
        else:
            self.single_file_max_size = 200 * ftp_v5.conf.common_config.GIGABYTE  # 默认单文件最大为200G

        self.min_part_size = 2 * ftp_v5.conf.common_config.MEGABYTE
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "min_part_size"):
            try:
                if int(cfg.get("OPTIONAL", "min_part_size")) > 0 and int(
                        cfg.get("OPTIONAL", "min_part_size")) < 5 * ftp_v5.conf.common_config.GIGABYTE:
                    self.min_part_size = int(cfg.get("OPTIONAL", "min_part_size"))
            except ValueError:
                pass
            except TypeError:
                pass

        self.upload_thread_num = cpu_count() * 4
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "upload_thread_num"):
            try:
                if int(cfg.get("OPTIONAL", "upload_thread_num")) > 0 and int(
                        cfg.get("OPTIONAL", "upload_thread_num")) <= cpu_count() * 8:
                    self.upload_thread_num = int(cfg.get("OPTIONAL", "upload_thread_num"))
            except ValueError:
                pass
            except TypeError:
                pass

        self.max_connection_num = 512
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "max_connection_num"):
            try:
                if int(cfg.get("OPTIONAL", "max_connection_num")) > 0:
                    self.max_connection_num = int(cfg.get("OPTIONAL", "max_connection_num"))
            except ValueError:
                pass
            except TypeError:
                pass

        self.max_list_file = 1000
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "max_list_file"):
            try:
                if int(cfg.get("OPTIONAL", "max_list_file")) > 0:
                    self.max_list_file = int(cfg.get("OPTIONAL", "max_list_file"))
            except ValueError:
                pass
            except TypeError:
                pass

        self.log_level = logging.INFO
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "log_level"):
            if str(cfg.get("OPTIONAL", "log_level")).lower() == str("INFO").lower():
                self.log_level = logging.INFO
            if str(cfg.get("OPTIONAL", "log_level")).lower() == str("DEBUG").lower():
                self.log_level = logging.DEBUG
            if str(cfg.get("OPTIONAL", "log_level")).lower() == str("ERROR").lower():
                self.log_level = logging.ERROR

        self.log_dir = "log"
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "log_dir"):
            self.log_dir = str(cfg.get("OPTIONAL", "log_dir")).lower()
        if not os.path.exists(self.log_dir):
            os.mkdir(self.log_dir)

        self.log_filename = "cos_v5.log"
        if str(self.log_dir).endswith("/"):
            self.log_filename = self.log_dir + self.log_filename
        else:
            self.log_filename = self.log_dir + "/" + self.log_filename

        self.log_rotate_enabled = False
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "log_rotate_enabled"):
            try:
                if str(cfg.get("OPTIONAL", "log_rotate_enabled")).lower() == str('yes') or\
                    str(cfg.get("OPTIONAL", "log_rotate_enabled")).lower() == str('true') or\
                    str(cfg.get("OPTIONAL", "log_rotate_enabled")).lower() == str('y'):
                    self.log_rotate_enabled = True
                else:
                    self.log_rotate_enabled = False
            except ValueError:
                pass
            except TypeError:
                pass

        # Y-%m-%d_%H-%M-%S
        self.log_rotate_when = 'H'
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "log_rotate_when"):
            try:
                # 秒级滚动，大小写兼容
                if str(cfg.get("OPTIONAL", "log_rotate_when")).lower() == str('s'):
                    self.log_rotate_when = 'S'
                # 分钟级
                elif str(cfg.get("OPTIONAL", "log_rotate_when")) == str('M'):
                    self.log_rotate_when = 'M'
                # 小时级，大小写兼容
                elif str(cfg.get("OPTIONAL", "log_rotate_when")).lower == str('H').lower:
                    self.log_rotate_when = 'H'
                # 最多到天级
                elif str(cfg.get("OPTIONAL", "log_rotate_when")).lower() == str('d').lower():
                    self.log_rotate_when = 'd'
                else:
                    self.log_rotate_when = 'H'
            except ValueError:
                pass
            except TypeError:
                pass

        self.log_backup_count = 100
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "log_backup_count"):
            try:
                if int(cfg.get("OPTIONAL", "log_backup_count")) > 0:
                    self.log_rotate_size = int(cfg.get("OPTIONAL", "log_backup_count"))
            except ValueError:
                pass
            except TypeError:
                pass

        CosFtpConfig._isInit = True

    def get_user_info(self, homedir):
        '''
        每个用户一个工作目录
        :param homedir:
        :return: 登录用户的信息
        '''

        return self.all_COS_UserInfo_Map.get(homedir, None)

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    def __str__(self):
        return "user_info: %s \n" \
               "user_list: %s \n" \
               "masquerade_address: %s \n" \
               "listen_port: %d \n" \
               "passive_ports: %s \n" \
               "single_file_max_size:%d \n" \
               "min_part_size: %d \n" \
               "upload_thread_num: %d \n" \
               "max_connection_num: %d \n" \
               "max_list_file: %d \n" \
               "log_level: %s \n" \
               "log_dir: %s \n" \
               "log_file_name: %s \n" % (
                   self.all_COS_UserInfo_Map, self.login_users, self.masquerade_address, self.listen_port,
                   self.passive_ports,
                   self.single_file_max_size, self.min_part_size, self.upload_thread_num, self.max_connection_num,
                   self.max_list_file, self.log_level, self.log_dir, self.log_filename)

    @classmethod
    def check_config(cls, ftp_config):
        """
        检查配置参数是否正确
        :return:
        """
        cfg = ConfigParser.RawConfigParser()
        cfg.read(CosFtpConfig.CONFIG_PATH)

        config_check_enable = True  # 默认开启配置检查
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "config_check_enable"):
            config_check_enable = cfg.getboolean("OPTIONAL", "config_check_enable")

        if not config_check_enable:
            return  # 跳过配置检查

        if ftp_config.single_file_max_size > 40 * 1000 * ftp_v5.conf.common_config.GIGABYTE:
            raise ValueError("Single file size can only support up to 40TB")

        # 先获取当前系统的物理内存
        part_size = ftp_config.min_part_size
        MaxiumPartNum = 10000
        if part_size < int(math.ceil(float(ftp_config.single_file_max_size) / MaxiumPartNum)):
            part_size = int(math.ceil(float(ftp_config.single_file_max_size) / MaxiumPartNum))

        if ftp_config.max_connection_num < 0:
            raise ValueError("max connection num must be greater or equal to 0")

        sys_available_memory = system_info.get_available_memory()

        # ftp进程的最大使用内存大约为：
        # 1. 每个控制连接大概会耗费1 -- 3MB内存
        # 2. 每个连接的list操作大约会耗费max_list_file KB
        # 3. 每个上传线程需要读取一个part_size的缓冲区，另外在上传到COS过程中，客户端又会向ftp服务端写入
        # 4. ftp server主线程大约耗费20MB
        each_connection_memory = (ftp_config.max_connection_num - 1) * 2 * ftp_v5.conf.common_config.MEGABYTE
        each_connection_list_memory = \
            ((ftp_config.max_connection_num - 1) / 2) * ftp_config.max_list_file * ftp_v5.conf.common_config.KILOBYTE
        upload_buffer_memory = (((ftp_config.max_connection_num - 1) / 2) + ftp_config.upload_thread_num) * part_size
        ftp_process_res = 20 * ftp_v5.conf.common_config.MEGABYTE

        require_memory = ftp_process_res + each_connection_memory + each_connection_list_memory + upload_buffer_memory

        if sys_available_memory * 0.6 < require_memory:
            raise ValueError("60% of the currently available memory is:{0}, and "
                             "cos ftp server requires a maximum of memory:{1}. "
                             "Please consider to decrease the max connection num or release some system memory."
                             "You can also disable the config check by setting 'config_check_enable' to false"
                             .format(sys_available_memory * 0.6, require_memory))


# unittest
if __name__ == "__main__":
    print
    CosFtpConfig.CONFIG_PATH

    print
    dir(CosFtpConfig())
    print
    dir(CosFtpConfig())
