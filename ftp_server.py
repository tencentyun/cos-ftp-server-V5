# -*- coding:utf-8 -*-

import sys
import logging


from pyftpdlib.servers import FTPServer, MultiprocessFTPServer

from ftp_v5.cos_authorizer import CosAuthorizer
from ftp_v5.cos_ftp_handler import CosFtpHandler
from ftp_v5.cos_file_system import CosFileSystem
from ftp_v5.conf.ftp_config import CosFtpConfig

logging.basicConfig(filename='pyftpd.log', level=logging.DEBUG)


def run(port=2121, passive_ports=range(60000, 65535), masquerade_address=None):
    print "starting  ftp server..."

    authorizer = CosAuthorizer()
    for login_user, login_password, permission in CosFtpConfig().login_users:
        perm = ""
        if "R" in permission:
            perm = perm + authorizer.read_perms
        if "W" in permission:
            perm = perm + authorizer.write_perms
        authorizer.add_user(login_user, login_password, CosFtpConfig().homedir, perm=perm)

    handler = CosFtpHandler
    handler.authorizer = authorizer
    handler.abstracted_fs = CosFileSystem
    handler.banner = "Welcome to COS FTP Service"
    handler.permit_foreign_addresses = True

    if masquerade_address is not None:
        handler.masquerade_address = masquerade_address

    handler.passive_ports = passive_ports

    server = MultiprocessFTPServer(("0.0.0.0", port), handler)

    server.serve_forever()


def main():
    port = CosFtpConfig().listen_port

    external_ip = CosFtpConfig().passive_address

    run(port=port, masquerade_address=external_ip)

if __name__ =="__main__":
    main()
