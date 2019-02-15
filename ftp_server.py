#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys

from ftp_v5 import server

reload(sys)
sys.setdefaultencoding('utf-8')

if __name__ == "__main__":
    server.main()
