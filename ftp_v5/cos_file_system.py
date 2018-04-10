# -*- coding:utf-8 -*-

from pyftpdlib.filesystems import AbstractedFS, FilesystemError
from ftp_v5.stream_uploader import StreamUploader
from os import path
from ftp_v5.utils import reformat_lm
from qcloud_cos.cos_exception import CosException
from qcloud_cos.cos_exception import CosServiceError
from qcloud_cos.cos_exception import CosClientError
from qcloud_cos.cos_client import CosS3Client
from qcloud_cos.cos_client import CosConfig
from ftp_v5.conf.ftp_config import CosFtpConfig
import urllib
import logging

logger = logging.getLogger(__name__)


class MockCosWriteFile(object):
    def __init__(self, file_system, bucket_name, filename):
        self._file_system = file_system
        self._bucket_name = bucket_name
        self._key_name = filename
        self._closed = False
        self._file_name = path.basename(filename)
        self._name = self._key_name

        self._uploader = StreamUploader(self._file_system.client, self._bucket_name, self._key_name)

    @property
    def name(self):
        return self._name

    def write(self, data):
        self._uploader.write(data)
        print "Recv data_len: %d, file: %s" % (len(data), self._key_name)
        return len(data)

    def close(self):
        logger.info("Closing file: {0}".format(self._key_name))
        try:
            self._uploader.close()
        except Exception as e:
            logger.exception("close the uploader occurs an exception. File: {0}".format(str(self._key_name).encode("utf-8")))
            raise FilesystemError("Upload failed. File:{0}".format(self._key_name))
        finally:
            logger.debug("Upload finish. File:{0}".format(self._key_name))
            self._closed = True

    @property
    def closed(self):
        return self._closed


class CosFileSystem(AbstractedFS):
    def __init__(self, *args, **kwargs):
        super(CosFileSystem, self).__init__(*args, **kwargs)
        self._cos_client = CosS3Client(CosConfig(Appid=CosFtpConfig().appid,
                                                 Region=CosFtpConfig().region,
                                                 Access_id=CosFtpConfig().secretid,
                                                 Access_key=CosFtpConfig().secretkey), retry=3)
        self._bucket_name = CosFtpConfig().bucket

    @property
    def client(self):
        return self._cos_client

    def realpath(self, path):                                                                           # 根目录在哪里？
        return path

    def open(self, filename, mode):
        logger.info("user invoke open to {0}".format(str(filename).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(filename, unicode), filename

        if self.isdir(filename):
            raise FilesystemError(filename + "is a directory")

        ftp_path = self.fs2ftp(filename)
        logger.debug("ftp_path: {0}".format(str(ftp_path).encode("utf-8")))
        key_name = ftp_path[1:]                 # 去除头部的"/"
        logger.debug("key_name: {0}".format(str(key_name)))

        if 'r' in mode:
            try:
                url = self._cos_client.get_presigned_download_url(Bucket=self._bucket_name, Key=key_name)
                fd = urllib.urlopen(url)
            except CosClientError as e:
                logger.exception("open file:{0} occurs a CosClientError.".format(str(ftp_path).encode("utf-8")))
                raise FilesystemError("Failed to open file {0} in read mode".format(str(ftp_path).encode("utf-8")))
            except CosServiceError as e:
                logger.exception("open file:{0} occurs a CosServiceError.".format(str(ftp_path).encode("utf-8")))
                raise FilesystemError("Failed to open file {0} in read mode".format(str(ftp_path).encode("utf-8")))
            except Exception as e:
                logger.exception("open file:{0} occurs an error.".format(str(ftp_path).encode("utf-8")))
                raise FilesystemError("Failed to open file {0} in read mode".format(str(ftp_path).encode("utf-8")))
            return fd
        else:
            return MockCosWriteFile(self, self._bucket_name, key_name)

    def getsize(self, path):
        logger.info("User invoke getsize to {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(path).encode("utf-8")))
        assert isinstance(path,unicode), path

        if self.isfile(path):
            key_name = self.fs2ftp(path).strip("/")
            try:
                response = self._cos_client.head_object(Bucket=self._bucket_name,
                                                        Key=key_name)
            except CosClientError as e:
                logger.exception("Get File:{0} size".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Failed to retrieve the file {0} attribute information.".format(str(key_name).encode("utf-8")))
            except CosServiceError as e:
                logger.exception("Get File:{0} size".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Failed to retrieve the file {0} attribute information".format(str(key_name).encode("utf-8")))
            except Exception as e:
                logger.exception("Get File:{0} size".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Failed to retrieve the file {0} attribute information".format(str(key_name).encode("utf-8")))
            return int(response["Content-Length"])
        elif self.isdir(path):
            return 0
        else:
            logger.error("Path: {0} is invalid!".format(str(path).encode("utf-8")))
            raise FilesystemError("Path: {0} is invalid!".format(str(path).encode("utf-8")))

    def chdir(self, path):
        logger.info("user invoke chdir to {0}".format(str(path).encode("utf-8")))
        logger.info("current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        if self.isdir(path):
            self._cwd = self.fs2ftp(path)
            logger.debug("current work directory {0}".format(str(self.cwd).encode("utf-8")))
        else:
            e = OSError()
            e.errno = 2
            e.filename = path
            e.strerror = "No such file or directory"
            raise e

    def mkdir(self, path):
        logger.info("user invoke mkdir of {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory: {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        if self.isdir(path):
            logger.error(path + " is a directory")
            raise FilesystemError(path + " is a directory")

        ftp_path = self.fs2ftp(path)
        logger.debug("ftp_path: {0}".format(str(ftp_path).encode("utf-8")))
        dir_name = ftp_path.strip("/") + "/"
        logger.debug("key_name: {0}".format(str(dir_name).encode("utf-8")))

        try:
            response = self._cos_client.put_object(Bucket=self._bucket_name, Body="",
                                                    Key=dir_name)
        except CosClientError as e:
            logger.exception("Make dir: {0} occurs an CosClientError.".format(str(dir_name).encode("utf-8")))
            raise FilesystemError("Make dir:{0} failed.".format(str(ftp_path).encode("utf-8")))
        except CosServiceError as e:
            logger.exception("Make dir: {0} occurs an CosServiceError.".format(str(dir_name).encode("utf-8")))
            raise FilesystemError("Make dir:{0} failed.".format(str(ftp_path).encode('utf-8')))
        except Exception as e:
            logger.exception("Make dir: {0} occurs an exception.".format(str(dir_name).encode("utf-8")))
            raise FilesystemError("Make dir:{0} failed".format(str(ftp_path).encode("utf-8")))

        logger.debug("response: {0}".format(str(response).encode("utf-8")))

    def rename(self, src, dest):
        logger.info("User invoke rename for {0} to {1}".format(str(src).encode("utf-8"), str(dest).encode("utf-8")))
        logger.info("Current work directory: {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(src, unicode), src
        assert isinstance(dest, unicode), dest

        if src == dest:
            return

        if self.isfile(src):
            src_key_name = self.fs2ftp(src)[1:]             # 去除头部的/
            dest_key_name = self.fs2ftp(dest)[1:]           # 去除头部的/

            copy_source = dict()
            copy_source["Bucket"] = self._bucket_name
            copy_source["Key"] = src_key_name               # XXX 该不该带斜线

            try:
                response = self._cos_client.copy_object(Bucket=self._bucket_name,
                                                        Key=dest_key_name,
                                                        CopySource=copy_source)
                self._cos_client.delete_object(
                    Bucket=self._bucket_name,
                    Key=src_key_name
                )
            except CosClientError as e:
                logger.exception("Rename " + str(src).encode("utf-8") + " to " + str(dest).encode("utf-8")
                                 + "occurs an CosClientError.")
                raise FilesystemError("Rename {0} to {1} failed.".format(str(src).encode("utf-8")), str(dest).encode("utf-8"))
            except CosServiceError as e:
                logger.exception("Rename " + str(src).encode("utf-8") + "to" + str(dest).encode("utf-8")
                                 + "occurs an CosServiceError.")
                raise FilesystemError("Rename {0} to {1} failed.".format(str(src).encode("utf-8"), str(dest).encode("utf-8")))
            except Exception as e:
                logger.exception("Rename " + str(src).encode("utf-8")+ "to" + str(dest).encode("utf-8") + "occurs an exception.")
                raise FilesystemError("Rename {0} to {1} failed.".format(str(src).encode("utf-8"),str(dest).encode("utf-8")))
        elif self.isdir(src):
            raise FilesystemError("Directory renaming is not supported")
        else:
            raise FilesystemError("Invalid parameter!")

    def _gen_list(self, response):
        logger.debug("Current work directory: {0}".format(self.cwd))
        list_name = list()
        list_dir = set()
        list_key = set()

        if "CommonPrefixes" in response and isinstance(response["CommonPrefixes"], dict):
            dir_path = "/" + response["CommonPrefixes"]["Prefix"]
            dir_name = dir_path[len(self.cwd):].strip("/")
            if dir_name != "":
                list_dir.add(("dir", 0, None, dir_name))

        if "CommonPrefixes" in response and isinstance(response["CommonPrefixes"],list):
            for common_prefix in response["CommonPrefixes"]:
                dir_path = "/" + common_prefix["Prefix"]
                dir_name = dir_path[len(self.cwd):].strip("/")
                if dir_name != "":
                    list_dir.add(("dir", 0, None, dir_name))

        if "Contents" in response and len(response["Contents"]) > 0:
            for key in response["Contents"]:
                key_path = "/" + key["Key"]
                key_name = key_path[len(self.cwd):].strip("/")

                if key_name == "":
                    continue

                if key_name.endswith("/"):
                    list_dir.add(("dir", 0, None, key_name))
                else:
                    list_key.add(("file", int(key['Size']), key['LastModified'], key_name))

        for dir in list_dir:
            list_name.append(dir)

        for key in list_key:
            list_name.append(key)

        return list(list_dir.union(list_key))

    def listdir(self, path):
        logger.info("user invoke listdir for {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        ftp_path = self.fs2ftp(path)
        logger.debug("ftp_path: {0}".format(str(ftp_path).encode("utf-8")))
        dir_name = ftp_path
        logger.debug("dir_name: {0}".format(str(dir_name).encode("utf-8")))

        list_name = list()
        max_list_file = CosFtpConfig().max_list_file
        if dir_name == "/":                                                     # 如果是根目录
            isTruncated= True
            next_marker = str("")
            while isTruncated and max_list_file > 0 and next_marker is not None:
                try:
                    response = self._cos_client.list_objects(Bucket=self._bucket_name,
                                                             Delimiter="/",
                                                             Marker=next_marker)
                    tmp_list = self._gen_list(response)
                    list_name.extend(tmp_list)
                    max_list_file -= len(tmp_list)
                    if response['IsTruncated'] == 'true':
                        isTruncated = True
                        next_marker = response['NextMarker']
                    else:
                        isTruncated = False
                except CosClientError as e:
                    logger.exception("List dir path: {0} occurs an CosClientError.".format(dir_name))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))
                except CosServiceError as e:
                    logger.exception("List dir path: {0} occurs an CosServiceError.".format(dir_name))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))
                except Exception as e:
                    logger.exception("List dir path: {0} occurs an unknown exception.".format(dir_name))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))

            return list_name

        if len(dir_name.split("/")) >= 2:                                       # 二级以上目录
            isTruncated = True
            next_marker = str("")
            while isTruncated and max_list_file > 0 and next_marker is not None:
                try:
                    response = self._cos_client.list_objects(Bucket=self._bucket_name,
                                                            Prefix=(dir_name.strip("/") + "/"),
                                                            Delimiter="/",
                                                            Marker=next_marker)
                    tmp_list = self._gen_list(response)
                    list_name.extend(tmp_list)
                    max_list_file -= len(tmp_list)
                    if response['IsTruncated'] == 'true':
                        isTruncated = True
                        next_marker = response['NextMarker']
                    else:
                        isTruncated = False
                except CosClientError as e:
                    logger.exception("List dir path: {0} occurs a CosClientError.".format(str(dir_name).encode("utf-8")))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))
                except CosServiceError as e:
                    logger.exception("List dir path: {0} occurs a CosServiceError.".format(str(dir_name).encode("utf-8")))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))
                except Exception as e:
                    logger.exception("List dir path: {0} occurs an unknown exception.".format(str(dir_name).encode("utf-8")))
                    raise FilesystemError("list dir:{0} failed.".format(ftp_path))
            return list_name

    def isfile(self, path):
        logger.info("user invoke isfile for {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        if path.startswith("/"):
            ftp_path = self.fs2ftp(path)
            key_name = ftp_path.strip("/")

            try:
                response = self._cos_client.list_objects(Bucket=self._bucket_name,
                                                         Prefix=key_name,               # 假设就是个文件
                                                         Delimiter="/")
                if "Contents" in response:
                    return True
                else:                                                                                   
                    return False
            except CosException:
                logger.error("Exception: {0}".format(str(CosException.message).encode("utf-8")))
                raise FilesystemError(CosException.message)
                return False
        else:
            return False

    def islink(self, fs_path):
        return False

    def isdir(self, path):                                                                              # xxx
        logger.info("User invoke isdir for {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(path).encode("utf-8")))
        assert isinstance(path, unicode), path

        if path.startswith("/"):
            ftp_path = self.fs2ftp(path)
            if ftp_path == "/":             # 根目录
                return True

            try:
                key_name = ftp_path.strip("/")
                response = self._cos_client.list_objects(Bucket=self._bucket_name,
                                                         Prefix=key_name,
                                                         Delimiter="/")
                if "CommonPrefixes" in response and isinstance(response["CommonPrefixes"], dict):
                    if response["CommonPrefixes"]["Prefix"] == key_name + "/":
                        return True
                    return False
                elif "CommonPrefixes" in response and isinstance(response["CommonPrefixes"], list):
                    for common_prefix in response["CommonPrefixes"]:
                        if common_prefix["Prefix"] == key_name + "/":
                            return True
                    return False
                else:
                    return False
            except CosException:
                logger.error("Exception: {0}".format(str(path).encode("utf-8")))
                return False
        else:
            return False

    def rmdir(self, path):
        logger.info("user invoke rmdir for {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        if self.isdir(path):
            dir_name = self.fs2ftp(path).strip("/") + "/"
            logger.debug("dir_name:{0}".format(str(dir_name).encode("utf-8")))
            response = self._cos_client.delete_object(Bucket=self._bucket_name, Key=dir_name)
            logger.debug("response:{0}".format(str(response).encode("utf-8")))

    def remove(self, path):
        logger.info("user invoke remove for {0}".format(str(path).encode("utf-8")))
        logger.info("Current work directory {0}".format(str(self.cwd).encode("utf-8")))
        assert isinstance(path, unicode), path

        if self.isfile(path):
            key_name = self.fs2ftp(path).strip("/")
            logger.debug("key_name: {0}".format(str(key_name).encode("utf-8")))
            try:
                response = self._cos_client.delete_object(Bucket=self._bucket_name, Key=key_name)
            except CosClientError as e:
                logger.exception("Remove file:{0} occurs a CosClientError.".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Remove file:{0} occurs error.".format(str(path).encode("utf-8")))
            except CosServiceError as e:
                logger.exception("Remove file:{0} occurs a CosServiceError.".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Remove file:{0} occurs error.".format(str(path).encode("utf-8")))
            except Exception as e:
                logger.exception("Remove file:{0} occurs an exception.".format(str(key_name).encode("utf-8")))
                raise FilesystemError("Remove file:{0} occurs error.".format(str(path).encode("utf-8")))
            logger.debug("response: {0}".format(str(response).encode("utf-8")))

    def lexists(self, path):
        logger.info("User invoke lexists for {0}".format(str(path).encode("utf-8")))
        ftp_path = self.fs2ftp(path)

        if ftp_path.startswith("/"):
            if self.isdir(path) or self.isfile(path):               # 如果路径
                return True
            else:
                return False
        return False

    def format_list(self, basedir, listing, ignore_err=True):
        for basename in listing:
            ft, size, last_modified, name = basename
            last_modified = reformat_lm(last_modified, form="ls")

            if ft == 'dir':
                perm = "rwxrwxrwx"
                t = 'd'
            else:
                perm = "r-xr-xr-x"
                t = '-'
            line = "%s%s\t1\towner\tgroup\t%s\t%s\t%s\r\n" % (t, perm, size, last_modified, name)
            yield line.encode("utf8", self.cmd_channel.unicode_errors)

    def format_mlsx(self, basedir, listing, perms, facts, ignore_err=True):
        for basename in listing:
            ft, size, last_modified, name = basename
            last_modified = reformat_lm(last_modified, form="mlsx")

            if ft == 'dir':
                perm = 'el'
            else:
                perm = 'r'
            line = "type=%s;size=%d;perm=%s;modify=%s %s\r\n" % (ft, size, perm, last_modified, name)
            yield line.encode("utf8", self.cmd_channel.unicode_errors)


def test():
    cos_client = CosS3Client(CosConfig(Appid=CosFtpConfig().appid,
                                       Access_id=CosFtpConfig().secretid,
                                       Access_key=CosFtpConfig().secretkey,
                                       Region=CosFtpConfig().region
                                       ))
if __name__ == "__main__":
    test()