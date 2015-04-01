---
layout: default.html
title: importing 
---

#importing a qcow2 disk into ovirt 3.5
###问题概述

之前使用virt-manager 创建的虚拟机，磁盘文件是qcow2格式的，想要将该虚拟机迁移到ovirt中，就要将其转换成ovf格式的，使用engine-image-uploader工具上传 OVF 格式的虚拟机镜像文件到指定 export 存储域。从而可以被 EayunOS 虚拟化管理中心自动识别。

###步骤
1. 在虚拟机所在的服务器上，使用[这里](../scripts/guest-image-ovf-creator.py)提供的脚本将qcow2格式的虚拟机镜像文件转换成ovf格式的。
   
   * 使用以下命令创建一个包含image 和 master 子目录的目录

   `guest-image-ovf-creator.py –disk=（qcow2文件路径）`
   
   * cd 到该目录，执行以下命令创建与映像上传程序兼容的 OVF 压缩文件

   `tar -zcvf my.ovf images/ master/`

   该步可以兼并到上一步，只需在上一步命令中添加参数--gzip即可。

2. 将该ovf文件scp到engine所在的服务器，准备上传。

3. 列出附加到engine上的导出存储域

   `engine-image-uploader list`

4. 将ovf文件上传到导出存储域中
   `engine-image-uploader -e [export domain name] upload my.ovf`

>**注意**
>
>由于该磁盘文件大小为50G ，而engine的硬盘容量只有50G，因此该步会出现临时目录空间不足的问题。暂时的解决办法如下：

1. 在别的有足够空间的服务器上安装 ovirt-image-uploader

   `yum install ovirt-image-uploader`

2. 将要上传的ovf文件scp到该服务器上，准备上传。

3. 由于不在engine所在的服务器，所以使用`engine-image-uploader list`找不到导出域，可以执行以下命令来代替：

   `engine-image-uploader -n [nfs server] upload my.ovf`

   >**注意**
   >
   >nfs server的写法：examage.com:/path/to/domain/<uuid>,例如：192.168.2.70：/home/exports/cb10c368-5918-42af-8c14-0173b437e1b8

4. 上传成功后，在engine的web界面上选择该导出存储域，在详细面板中点击模板导入标签，列表中显示了刚上传的镜像文件。

5. 选择该模板，点击**导入**，开始模板导入过程。

6. 导入模板成功，可以基于该模板创建虚拟机了。
