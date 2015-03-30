---
layout:default
title:lvm练习
---
# lvm练习
### 创建一个LV
* 磁盘分区：fdisk 装置名，如fdisk /dev/vda
* 将分区的system id改成8e，标记为lvm：
   fdisk /dev/vda
   t
    分区号
   8e
* pvcreate：pvcreate /dev/vda{1,2,3...}
* vgcreate：vgcreate -s [PE 大小（默认4M）] vg名  /dev/vda{1,2,3...}
* lvcreate：lvcreate -L [size] -n lv名 vg名
* mkfs -t lv名（注意是全路径/dev/vg名/lv名）
* 挂载：mount /dev/vg名/lv名  /mnt/lvm
* 查看
   pv:pvdisplay
   vg:vgdisplay
   lv:lvdisplay
### 扩大lv容量：
* 分区，创建pv
* vgextend:vgextend /pv路径  vg名
* lvresize -L [size] lv路径
* 查看lv：lvdisplay
* 查看/mnt/lvm大小：df /mnt/lvm(没有扩大)
* resize2fs lv路径  [size]
* 查看/mnt/lvm大小(扩大了)
### 缩小lv容量
* resize2fs lv路径 [size](不支持在线缩小容量，所以先解挂)
* umount  lv路径  /mnt/lvm
* resize2fs lv路径 [size]
* 再挂载上去：mount lv名 /mnt/lvm
* 查看/mnt/lvm容量：df /mnt/lvm(缩小了)
###--------------------------------- 若想将某个pv抽离vg，继续
* pvdisplay查看那个pv没有使用
* vgreduce vg名 pv   再查看vg大小，确实小了。
* pvremove pv
* 将该分区的system id 改回83
### 删除并关闭lvm
* 解挂 ：umount
* lvremove lv路径
* vgchange -a n vg名，将vg取消激活态
* vgremove vg名
* pvremove /dev/vda{1,2,3...}
* 将所有分区system id 改回83

