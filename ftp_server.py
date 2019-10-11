#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys

from ftp_v5 import server

try:
   # for python 2
   reload(sys)
   sys.setdefaultencoding('utf-8')
except:
   # for python 3
   ""
if __name__ == "__main__":
    server.main()
