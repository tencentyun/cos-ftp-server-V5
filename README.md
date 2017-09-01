COS FTP SERVER支持通过FTP协议直接操作COS中的对象和目录


功能说明
--------------------------------------------------------------

**上传机制**：流式上传COS，不落本地磁盘（但是仍然需要按照标准FTP协议配置工作目录）

**下载机制**：流式下载（通过返回文件的描述符给客户端）

**目录机制**: bucket作为整个FTP SERVER的根目录， bucket下面可以建立若干个的子目录。

**Note**：	目前只支持操作一个bucket，后期可能会支持同时操作多个bucket。


支持的FTP命令
-------------------------------------------------------------------------

- put
- mput
- get
- mget
- delete
- mkdir
- ls
- cd
- bye
- quite
- size


不支持FTP命令
----------------------------------------------------

- append

**Note**：Ftp Server工具暂时不支持断点续传功能


适用的COS版本
----------------------------------------------------
COS V5

系统与运行环境要求
----------------------------------------------------

操作系统： Linux (推荐使用腾讯Centos系列CVM)
解释器版本： Python 2.7
依赖库： cos-python-sdk-v5（included）， pyftpdlib(included)

配置文件
----------------------------------------------------

conf/vsftpd.conf为FTP SERVER的配置文件，相关配置说明如下

``` conf

[COS_ACCOUNT]
cos_appid = xxxxx		# 用户自己appid
cos_secretid= xxxx	    #
cos_secretkey = xxxx    # secretid对应的secretkey
cos_bucket = xxxxx		# 要操作的bucket的名字， Note：V5控制台上的bucket名字采用了bucketname-appid的命名，这里的只填写bucket_name
cos_region = gz			# bucket所在的区域，目前有效值为华南广州（gz），华东上海（sh），华北天津（tj）
cos_download_domain = cos
cos_user_home_dir = /home/test/cosftp_data	#ftp server的工作目录

[FTP_ACCOUNT]
login_users = user1:pass1:RW;user2:pass2:RW 这里配置ftp登录用户名、密码和相关的权限（格式为用户名：密码：读写权限，多个账户用分号分割）

[NETWORK]
passive_address = xxx.xxx.xxx.xxx	# 外网IP设置，用户如需要通过外网IP访问FTP服务器，则需要设置该项。 如客户机和FTP服务器均在腾讯云CVM机器上，通过内网IP访问，则不需要设置
listen_port = 2121		# FTP SERVER的监听端口，默认为2121

```

运行
------------------------------------------------------------

正确填写配置文件后，直接通过Python运行根目录下的ftp_server.py即可启动FTP SERVER：`python ftp_server.py`，也可以配合screen的命令将ftp server放到后台运行。


停止
-------------------------------------------------------------
` Ctrl + C` 即可取消server运行
