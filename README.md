# FTP SERVER 工具

COS FTP SERVER 支持通过FTP协议直接操作COS中的对象和目录，包括上传文件、下载文件、删除文件以及创建文件夹等

## 使用环境

### 系统环境

操作系统：Linux，推荐使用腾讯CentOS系列CVM

Python解释器版本：Python 2.7

依赖库：

- requests
- argparse

### 安装方法

直接运行cos ftp server目录下的setup.py即可，需要联网安装依赖库。

```
python setup.py install   # 这里可能需要sudo或者root权限
```

如果requests和argparse库等依赖已经安装了的话，可以直接运行ftp_server.py启动ftp server


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

conf/vsftpd.conf.example为Ftp Server工具的配置文件示例，请copy为vsftpd.conf，并按照以下的配置项进行配置：

``` conf
[COS_ACCOUNT]
cos_secretid = XXXXXX					# secretid和secretkey 可以在以下地址获取：https://console.qcloud.com/capi
cos_secretkey = XXXXXX
cos_bucket = {bucket}-{appid}	      # 要操作的bucket，bucket的格式为：bucektname-appid组成。 针对COS V5用户，这里与V5控制台上显示一致。例如：qcloud-12xxxxx
cos_region = ap-xxx					  # bucket所在的区域，目前支持的区域请参照官方文档【适用于XML API部分】：https://www.qcloud.com/document/product/436/6224
cos_user_home_dir = /home/cos_ftp/data   # Ftp Server的工作目录
[FTP_ACCOUNT]
login_users = user1:pass1:RW;user2:pass2:RW     # FTP 账户配置。配置格式为“用户名:密码:读写权限”，多个账户用分号分割

[NETWORK]
masquerade_address = XXX.XXX.XXX.XXX        # 如果FTP SERVER处于某个网关或NAT后，可以通过该配置项将网关的IP地址或域名指定给FTP
listen_port = 2121					   # Ftp Server的监听端口，默认为2121，注意防火墙需要放行该端口

passive_ports = 60000,65535             # #passive_port可以设置passive模式下，端口的选择范围，默认在(60000, 65535)区间上选择

[FILE_OPTION]
# 默认单文件大小最大支持到200G，不建议设置太大
single_file_max_size = 21474836480

[OPTIONAL]
# 以下设置，如无特殊需要，建议保留default设置  如需设置，请合理填写一个整数
min_part_size       = default
upload_thread_num   = default
max_connection_num  = 512
max_list_file       = 10000                # ls命令最大可列出的文件数目，建议不要设置太大，否则ls命令延时会很高
log_level           = INFO                 # 设置日志输出的级别
log_dir             = log                  # 设置日志的存放目录，默认是在ftp server目录下的log目录中

```

上述的OPTIONAL选项是提供给高级用户用于调整上传性能的可选项，根据机器的性能合理地调整上传分片的大小和并发上传的线程数，可以获得更好的上传速度，一般用户不需要调整，保持默认值即可。
同时，提供最大连接数的限制选项。 这里如果不想限制最大连接数，可以填写0，即表示不限制最大连接数目（不过需要根据您机器的性能合理评估）。

## 运行方法

正确填写配置文件后，直接通过Python运行根目录下的ftp_server.py即可启动FTP SERVER：python ftp_server.py，也可以配合screen的命令将ftp server放到后台运行。

## 停止

Ctrl + C 即可取消server运行（直接运行，或screen方式放在后台运行）

## FAQ

**配置文件中的masquerade_address这个选项有何作用？何时需要配置masquerade_address**

答：当FTP Server运行在一个多网卡的Server，并且FTP Server采用了PASSIVE模式（一般地，FTP客户端位于一个NAT网关之后时，都需要启用PASSIVE模式），此时需要使用masquerade_address选项来唯一绑定一个passive模式下用于reply的IP。
例如，FTP Server有多个IP地址，如内网IP为10.XXX.XXX.XXX，外网IP为123.XXX.XXX.XXX。 客户端通过外网IP连接到FTP Server，同时客户端使用的是PASSIVE模式传输，此时，若FTP Server未指定masquerade_address具体绑定到外网IP地址，则Server在passive模式下，reply时，有可能会走内网地址。就会出现客户端能连接上Ftp server，但是不能从Server端获取任何数据回复。

如果需要配置masquerade_address，建议指定为客户端连接Server所使用的那个IP地址。

**上传大文件的时候，如果中途取消，为什么COS上会留有已上传的文件**

答：由于新版的Ftp Server提供了完全的流式上传特性，如果用户的取消或者断开，都会触发大文件的上传完成操作，因此，COS会认为用户已经数据流上传完成，就会将已经上传的数据组成一个完整的文件。 如果，用户希望重新上传，可以直接以原文件名上传覆盖即可。也可以手动删除不完整的文件，重新上传。

**为什么Ftp Server配置中要设置最大上传文件的限制？**
答：由于COS的分片上传数目最大只能为10000块，且每个分片的大小限制为1MB ~ 5G。 这里设置最大上传文件的限制是为了合理计算一个上传分片的大小。默认支持200G以内的单文件上传，但是不建议用户设置过大，因为单文件大小设置越大，上传时的分片缓冲区也会相应的增大，这可能会耗费用户的内存资源。因此，建议用户根据自己的实际情况，合理设置单文件的大小限制。

**如果上传的文件超过最大限制，会怎么样？**
答：当实际上传的单文件大小超过了配置文件中的限制，则会抛出一个IOError的异常，并且在日志中标注错误信息。