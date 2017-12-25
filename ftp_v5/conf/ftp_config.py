# -*- coding:utf-8 -*-

import os
import ConfigParser
import platform
import logging
import ftp_v5.conf.common_config

from multiprocessing import cpu_count

logger = logging.getLogger(__name__)


class CosFtpConfig:

    CONFIG_PATH = None
    if platform.system() == "Windows":
        CONFIG_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))) + \
                                      "\\conf\\vsftpd.conf"
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

    def __init__(self):
        cfg = ConfigParser.RawConfigParser()
        cfg.read(CosFtpConfig.CONFIG_PATH)

        self.secretid = cfg.get("COS_ACCOUNT", "cos_secretid")
        self.secretkey = cfg.get("COS_ACCOUNT", "cos_secretkey")

        if cfg.has_section("COS_ACCOUNT") and cfg.has_option("COS_ACCOUNT", "cos_bucket"):
            tmp_bucket = cfg.get("COS_ACCOUNT", "cos_bucket")
            if len(str(tmp_bucket).split("-")) < 2:
                raise ValueError("Config error: bucket field must be {bucket name}-{appid}")
            try:
                str_list = str(tmp_bucket).split("-")
                self.appid = int(str_list[-1])                      # 目前，这里的appid必须为一个number
                del str_list[-1]
                self.bucket = "-".join(str_list)
            except TypeError:
                raise ValueError("Config error: bucket field must be {bucket name}-{appid}")
            except ValueError:
                raise ValueError("Config error: bucket field must be {bucket name}-{appid}")

        self.region = cfg.get("COS_ACCOUNT", "cos_region")
        self.homedir = cfg.get("COS_ACCOUNT", "cos_user_home_dir")

        login_users = cfg.get("FTP_ACCOUNT", "login_users")
        login_users = login_users.strip(" ").split(";")
        self.login_users = list()
        # self.login_users 的结构为 [ (user1,pass1,RW), (user2,pass2,RW) ]
        for element in login_users:
            login_user = element.split(":")
            self.login_users.append(tuple(login_user))

        self.masquerade_address = None
        if cfg.has_section("NETWORK") and cfg.has_option("NETWORK", "masquerade_address") and str(cfg.get("NETWORK", "masquerade_address")) != "":
            if CosFtpConfig._check_ipv4(cfg.get("NETWORK", "masquerade_address")):
                self.masquerade_address = cfg.get("NETWORK", "masquerade_address")
        else:
            self.masquerade_address = None

        self.listen_port = int(cfg.get("NETWORK", "listen_port"))
        passive_ports =cfg.get("NETWORK", 'passive_port').split(',')
        if len(passive_ports) > 1:
            self.passive_ports = range(int(passive_ports[0]), int(passive_ports[1]))
        elif len(passive_ports) == 1:
            self.passive_ports = range(int(passive_ports[0]), 65535)
        else:
            self.passive_ports = range(60000, 65535)

        if cfg.has_section("FILE_OPTION") and cfg.has_option("FILE_OPTION", "single_file_max_size"):
            self.single_file_max_size = int(cfg.get("FILE_OPTION", "single_file_max_size"))
        else:
            self.single_file_max_size = 200 * ftp_v5.conf.common_config.GIGABYTE                            # 默认单文件最大为200G

        self.min_part_size = 2 * ftp_v5.conf.common_config.MEGABYTE
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "min_part_size"):
            try:
                if int(cfg.get("OPTIONAL","min_part_size")) > 0 and int(cfg.get("OPTIONAL", "min_part_size")) < 5 * ftp_v5.conf.common_config.GIGABYTE:
                    self.min_part_size = int(cfg.get("OPTIONAL", "min_part_size"))
            except ValueError:
                pass
            except TypeError:
                pass

        self.upload_thread_num = cpu_count() * 4
        if cfg.has_section("OPTIONAL") and cfg.has_option("OPTIONAL", "upload_thread_num"):
            try:
                if int(cfg.get("OPTIONAL", "upload_thread_num")) > 0 and int(cfg.get("OPTIONAL", "upload_thread_num")) <= cpu_count() * 8:
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

    def __repr__(self):
        return "%s()" % self.__class__.__name__

    def __str__(self):
        return "appid: %s \n" \
               "secretid: %s \n" \
               "secretekey: %s \n" \
               "bucket: %s \n" \
               "region: %s \n" \
               "homedir:%s \n" \
               "login_users: %s \n" \
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
               "log_file_name: %s \n" % (self.appid, self.secretid, self.secretkey, self.bucket, self.region, self.homedir,
                                       self.login_users, self.masquerade_address, self.listen_port, self.passive_ports, self.single_file_max_size, self.min_part_size, self.upload_thread_num, self.max_connection_num,
                                       self.max_list_file, self.log_level, self.log_dir, self.log_filename)

# unittest
if __name__ == "__main__":

    print CosFtpConfig.CONFIG_PATH

    print CosFtpConfig()
