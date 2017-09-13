# -*- coding:utf-8 -*-

import os
import ConfigParser
import platform
import logging
import ftp_v5.conf.common_config

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

        self.appid = cfg.get("COS_ACCOUNT", "cos_appid")
        self.secretid = cfg.get("COS_ACCOUNT", "cos_secretid")
        self.secretkey = cfg.get("COS_ACCOUNT", "cos_secretkey")
        self.bucket = cfg.get("COS_ACCOUNT", "cos_bucket")
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

        self.listen_port = cfg.get("NETWORK", "listen_port")

        if cfg.has_section("FILE_OPTION") and cfg.has_option("FILE_OPTION", "single_file_max_size"):
            self.single_file_max_size = int(cfg.get("FILE_OPTION", "single_file_max_size"))
        else:
            self.single_file_max_size = 200 * ftp_v5.conf.common_config.GIGABYTE                            # 默认单文件最大为200G

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
               "listen_port: %s \n"\
               "single_file_max_size:%d \n" % (self.appid, self.secretid, self.secretkey, self.bucket, self.region, self.homedir,
                                       self.login_users, self.masquerade_address, self.listen_port, self.single_file_max_size)

# unittest
if __name__ == "__main__":

    print CosFtpConfig.CONFIG_PATH

    print CosFtpConfig()
