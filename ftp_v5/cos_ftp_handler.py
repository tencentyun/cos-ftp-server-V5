# -*- coding:utf-8 -*-

from pyftpdlib.handlers import FTPHandler


class CosFtpHandler(FTPHandler):
    def __init__(self, *args, **kwargs):
        FTPHandler.__init__(self, *args, **kwargs)

    def on_logout(self, username):
        del self.authorizer.user_table[username]