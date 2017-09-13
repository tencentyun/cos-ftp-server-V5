# FTP SERVER 工具

COS FTP SERVER 支持通过FTP协议直接操作COS中的对象和目录，包括上传文件、下载文件、删除文件以及创建文件夹等

## 使用环境

### 系统环境

操作系统：Linux，推荐使用腾讯CentOS系列CVM

Python解释器版本：Python 2.7

依赖库：

- cos-python-sdk-v5(included)
- pyftpdlib(included)

### 使用限制

适用于COS V5 版本


## 功能说明

**上传机制**：流式上传，不落本地磁盘，只要按照标准的FTP协议配置工作目录即可，不占用实际的磁盘存储空间。

**下载机制**：直接流式返回给客户端

**目录机制**：bucket作为整个FTP SERVER的根目录，bucket下面可以建立若干个子目录

**说明**：目前只支持操作一个bucket，后期可能会支持同时操作多个bucket。

## 支持的FTP Server命令

- put
- mput
- get
- rename
- delete
- mkdir
- ls
- cd
- bye
- quite
- size

## 不支持FTP命令
- append
- mget (不支持原生的mget命令，但在某些Windows客户端下，仍然可以批量下载，如FileZilla)

**说明**：Ftp Server工具暂时不支持断点续传功能


## 配置文件

conf/vsftpd.conf为Ftp Server工具的配置文件，相关配置项的说明如下：

``` conf
[COS_ACCOUNT]
cos_appid = 12XXXXXX					 # 用户自己的appid
cos_secretid = XXXXXX					# secretid和secretkey 可以在以下地址获取：https://console.qcloud.com/capi
cos_secretkey = XXXXXX
cos_bucket = XXXXX					   # 要操作的bucket名字，需要注意的是COS V5控制台上的bucket采用了bucket-appid的命名方式，这里只填写bucket即可
cos_region = ap-xxx					  # bucket所在的区域，目前支持的区域请参照官方文档【适用于XML API部分】：https://www.qcloud.com/document/product/436/6224
cos_user_home_dir = /home/cos_ftp/data   # Ftp Server的工作目录
[FTP_ACCOUNT]
login_users = user1:pass1:RW;user2:pass2:RW     # FTP 账户配置。配置格式为“用户名:密码:读写权限”，多个账户用分号分割

[NETWORK]
masquerade_address = XXX.XXX.XXX.XXX        # 如果FTP SERVER处于某个网关或NAT后，可以通过该配置项将网关的IP地址或域名指定给FTP
listen_port = 2121					   # Ftp Server的监听端口，默认为2121，注意防火墙需要放行该端口

[FILE_OPTION]
# 默认单文件大小最大支持到200G，不建议设置太大
single_file_max_size = 21474836480

```

## 运行方法

正确填写配置文件后，直接通过Python运行根目录下的ftp_server.py即可启动FTP SERVER：python ftp_server.py，也可以配合screen的命令将ftp server放到后台运行。

## 停止

Ctrl + C 即可取消server运行（直接运行，或screen方式放在后台运行）
