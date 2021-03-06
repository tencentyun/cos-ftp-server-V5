# -*- coding:utf-8 -*-

from pyftpdlib.authorizers import DummyAuthorizer, AuthenticationFailed

from ftp_v5.conf.ftp_config import CosFtpConfig


class CosAuthorizer(DummyAuthorizer):

    def __init__(self, *args, **kwargs):
        DummyAuthorizer.__init__(self, *args, **kwargs)

    def validate_authentication(self, user_name, password, handler):
        for login_user_name, login_password, home_dir, login_permission in CosFtpConfig().login_users:
            if user_name == login_user_name and password == login_password:
                return True

        raise AuthenticationFailed
