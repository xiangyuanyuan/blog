#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# guest-image-ovf-creator.py - Copyright (C) 2013 Red Hat, Inc.
# Written by Joey Boggs <jboggs@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.  A copy of the GNU General Public License is
# also available at http://www.gnu.org/copyleft/gpl.html.

import logging
import optparse
import os
import shutil
import struct
import sys
import tarfile
import tempfile
import time
import uuid

LOG_PREFIX = "guest-image-ovf-creator"
OVF_VERSION = "3.3.0.0"

XML_TEMPLATE = """<image>
  <name version='6.5' release='1'>%(NVR)s</name>
  <domain>
    <boot type='hvm'>
      <guest>
        <arch>x86_64</arch>
      </guest>
      <os>
        <loader dev='hd'/>
      </os>
      <drive disk='%(NVR)s.qcow2' target='hda'/>
    </boot>
    <devices>
      <vcpu>1</vcpu>
      <memory>524288</memory>
      <interface/>
      <graphics/>
    </devices>
  </domain>
  <storage>
    <disk file='%(NVR)s.qcow2' use='system' format='qcow2'/>
  </storage>
</image>"""

OVF_TEMPLATE = """
<ovf:Envelope xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1/" \
xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/\
CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem\
/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi=\
"http://www.w3.org/2001/XMLSchema-instance" ovf:version="%(ovf_version)s">
  <References>
    <File ovf:description="%(product_name)s" ovf:href="%(disk_path)s"\
 ovf:id="%(disk_file_name)s" ovf:size="%(raw_disk_size)s"/>
  </References>
  <Section xsi:type="ovf:NetworkSection_Type">
    <Info>List of Networks</Info>
  </Section>
  <Section xsi:type="ovf:DiskSection_Type">
    <Disk ovf:actual_size="%(disk_size_gb)s" ovf:boot="true"\
 ovf:disk-interface="VirtIO" ovf:disk-type="System"\
 ovf:diskId="%(disk_file_name)s" ovf:fileRef="%(disk_path)s"\
 ovf:format="http://www.vmware.com/specifications/vmdk.html#sparse"\
 ovf:parentRef="" ovf:size="%(disk_size_gb)s"\
 ovf:vm_snapshot_id="%(snapshot_id)s"\
 ovf:volume-format="COW" ovf:volume-type="Sparse"\
 ovf:wipe-after-delete="false"/>
  </Section>
  <Content ovf:id="out" xsi:type="ovf:VirtualSystem_Type">
    <Name>%(product_name)s</Name>
    <TemplateId>%(product_name)s</TemplateId>
    <Description>%(product_name)s</Description>
    <Domain/>
    <CreationDate>%(timestamp)s</CreationDate>
    <TimeZone/>
    <IsAutoSuspend>false</IsAutoSuspend>
    <VmType>1</VmType>
    <default_display_type>1</default_display_type>
    <default_boot_sequence>1</default_boot_sequence>
    <Section ovf:id="f9350d95-31b7-41d4-87ac-1526fa1435ab" \
ovf:required="false" xsi:type="ovf:OperatingSystemSection_Type">
      <Info>Guest OS</Info>
      <Description>rhel_7x64</Description>
    </Section>
    <Section xsi:type="ovf:VirtualHardwareSection_Type">
      <Info>1 CPU, 512 Memory</Info>
      <System>
        <vssd:VirtualSystemType>RHEVM 4.6.0.163</vssd:VirtualSystemType>
      </System>
      <Item>
        <rasd:Caption>1 virtual CPU</rasd:Caption>
        <rasd:Description>Number of virtual CPU</rasd:Description>
        <rasd:InstanceId>1</rasd:InstanceId>
        <rasd:ResourceType>3</rasd:ResourceType>
        <rasd:num_of_sockets>1</rasd:num_of_sockets>
        <rasd:cpu_per_socket>1</rasd:cpu_per_socket>
      </Item>
      <Item>
        <rasd:Caption>512 MB of memory</rasd:Caption>
        <rasd:Description>Memory Size</rasd:Description>
        <rasd:InstanceId>2</rasd:InstanceId>
        <rasd:ResourceType>4</rasd:ResourceType>
        <rasd:AllocationUnits>MegaBytes</rasd:AllocationUnits>
        <rasd:VirtualQuantity>512</rasd:VirtualQuantity>
      </Item>
      <Item>
        <rasd:Caption>Drive 1</rasd:Caption>
        <rasd:InstanceId>%(disk_file_name)s</rasd:InstanceId>
        <rasd:ResourceType>17</rasd:ResourceType>
        <rasd:HostResource>%(disk_path)s</rasd:HostResource>
        <rasd:Parent>00000000-0000-0000-0000-000000000000</rasd:Parent>
        <rasd:Template>00000000-0000-0000-0000-000000000000</rasd:Template>
        <rasd:ApplicationList/>
        <rasd:StorageId>00000000-0000-0000-0000-000000000000</rasd:StorageId>
        <rasd:StoragePoolId>%(storage_pool_id)s</rasd:StoragePoolId>
        <rasd:CreationDate>%(timestamp)s</rasd:CreationDate>
        <rasd:LastModified>%(timestamp)s</rasd:LastModified>
      </Item>
      <Item>
        <rasd:Caption>Ethernet 0 rhevm</rasd:Caption>
        <rasd:InstanceId>3</rasd:InstanceId>
        <rasd:ResourceType>10</rasd:ResourceType>
        <rasd:ResourceSubType>3</rasd:ResourceSubType>
        <rasd:Connection>rhevm</rasd:Connection>
        <rasd:Name>eth0</rasd:Name>
        <rasd:speed>1000</rasd:speed>
      </Item>
      <Item>
        <rasd:Caption>Graphics</rasd:Caption>
        <rasd:InstanceId>5</rasd:InstanceId>
        <rasd:ResourceType>20</rasd:ResourceType>
        <rasd:VirtualQuantity>1</rasd:VirtualQuantity>
      </Item>
    </Section>
  </Content>
</ovf:Envelope>
"""

DISK_META_TEMPLATE = """DOMAIN=%(domain_uuid)s
VOLTYPE=LEAF
CTIME=%(create_time)s
FORMAT=COW
IMAGE=%(image_uuid)s
DISKTYPE=1
PUUID=00000000-0000-0000-0000-000000000000
LEGALITY=LEGAL
MTIME=%(create_time)s
POOL_UUID=%(pool_id)s
SIZE=%(disk_size)s
TYPE=SPARSE
DESCRIPTION=%(description)s
EOF"""


def initLogger():
    logger = logging.getLogger(LOG_PREFIX)
    log_file = "/tmp/ovf-creator.log"
    formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)-8s - '
                                  '%(message)s')
    conformatter = logging.Formatter('%(levelname)-8s'
                                     ' %(message)s')
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(conformatter)
    logger.addHandler(console)


class Base(object):
    def __init__(self):
        self._logger = logging.getLogger(
            '%s.%s' % (LOG_PREFIX, self.__class__.__name__))


class OVFCreator(Base):

    def __init__(self):
        super(OVFCreator, self).__init__()
        self._parse_options()
        if self._options.output:
            if not os.path.isdir(self._options.output):
                raise RuntimeError("Output path is not a directory")
            self._tmp_dir = self._options.output
        else:
            self._tmp_dir = tempfile.mkdtemp()

        self._image_name = os.path.basename(os.path.splitext(
                                            self._options.disk)[0])
        self._logger.info("Image Name: %s" % self._image_name)
        self._raw_create_time = time.time()
        self._create_time = time.gmtime(self._raw_create_time)
        self._images_dir = os.path.join(self._tmp_dir, "images")
        self._master_dir = os.path.join(self._tmp_dir, "master")
        self._images_vm_dir = os.path.join(self._images_dir, self._image_name)
        self._master_vms_dir = os.path.join(self._master_dir, "vms")
        self._master_dest_dir = os.path.join(self._master_vms_dir,
                                             self._image_name)
        self._ovf_template_dest = os.path.join(self._master_dest_dir,
                                               self._image_name + ".ovf")
        self._meta_template_dest = os.path.join(self._images_vm_dir,
                                                self._image_name + ".meta")
        self._xml_template_dest = os.path.join(self._tmp_dir, self._image_name +
                                                ".xml")
        self._disk_dest = os.path.join(self._images_vm_dir, self._image_name)
        self.rel_disk_path = os.path.join(self._image_name, self._image_name)
        self._logger.info("OVF Template: %s" % self._ovf_template_dest)
        self._logger.info("XML Template: %s" % self._xml_template_dest)
        self._logger.info("Disk Destination: %s" % self._disk_dest)

    def _parse_options(self):
        parser = optparse.OptionParser()
        parser.add_option("--disk", type="string", dest="disk",
                          metavar="FILE", help="Disk image to create ovf"
                          "archive from")
        parser.add_option("--output", type="string", dest="output",
                          metavar="DIRECTORY", help="Disk image to create ovf"
                          "archive from")
        parser.add_option("--release", type="string", dest="release",
                          help="Release String")
        parser.add_option("--symlink", action="store_true", dest="symlink",
                          metavar="FILE", default=False,
                          help="Create a gzip archive")
        parser.add_option("--gzip", action="store_true", dest="gzip",
                          metavar="FILE", default=False,
                          help="Create a gzip archive")
        (self._options, args) = parser.parse_args()
        if not self._options.disk:
            raise RuntimeError("An input disk image must be defined")
        elif not os.path.exists(self._options.disk):
            raise RuntimeError("Image path is invalid")

    def _create_dir_structure(self):
        uid = 36  # vdsm user
        gid = 36  # kvm group
        for d in [self._images_dir, self._images_vm_dir, self._master_dir,
                  self._master_vms_dir, self._master_dest_dir]:
            os.mkdir(d)
            try:
                os.chown(d, uid, gid)
            except:
                self._logger.error("Unable to chown directory: %s" % d)

    def _get_qcow_size(self):
        qcow_struct = ">IIQIIQIIQQIIQ"  # > means big-endian
        qcow_magic = 0x514649FB  # 'Q' 'F' 'I' 0xFB
        f = open(self._options.disk, "r")
        pack = f.read(struct.calcsize(qcow_struct))
        f.close()
        try:
            unpack = struct.unpack(qcow_struct, pack)
            if unpack[0] == qcow_magic:
                size = unpack[5]
        except:
            raise RuntimeError("Unable to determine disk size")
        return size

    def _write_ovf_template(self):
        disk_size = self._get_qcow_size()
        ovf_dict = {"product_name": self._image_name,
                    "ovf_version": OVF_VERSION,
                    "disk_path": self.rel_disk_path,
                    "disk_file_name": os.path.basename(self.rel_disk_path),
                    "snapshot_id": str(uuid.uuid4()),
                    "storage_pool_id": str(uuid.uuid4()),
                    "raw_disk_size": disk_size,
                    "disk_size_gb": disk_size / (1024 * 1024 * 1024),
                    "timestamp": time.strftime("%Y/%m/%d %H:%M:%S",
                                               self._create_time)
                    }
        self._logger.info("Writing OVF Template")
        try:
            with open(self._ovf_template_dest, "w") as f:
                f.write(OVF_TEMPLATE % ovf_dict)
        except:
            raise RuntimeError("Unable to write ovf template")

    def _write_meta_template(self):
        disk_size = self._get_qcow_size() / 512
        meta_dict = {"domain": self._image_name,
                     "create_time": str(int(self._raw_create_time)),
                     "domain_uuid": str(uuid.uuid4()),
                     "image_uuid": str(uuid.uuid4()),
                     "pool_id": str(uuid.uuid4()),
                     "pool_uuid": str(uuid.uuid4()),
                     "description": self._image_name,
                     "disk_size": disk_size
                     }
        self._logger.debug(DISK_META_TEMPLATE)
        self._logger.debug(meta_dict)
        self._logger.info("Writing Metadata Template")
        try:
            with open(self._meta_template_dest, "w") as f:
                f.write(DISK_META_TEMPLATE % meta_dict)
        except:
            raise RuntimeError("Unable to write meta template")

    def _write_xml_template(self):
        xml_dict = {"NVR": self._options.release,
                     }
        self._logger.debug(XML_TEMPLATE)
        self._logger.debug(xml_dict)
        self._logger.info("Writing xml template")
        #try:
        with open(self._xml_template_dest, "w") as f:
            f.write(XML_TEMPLATE % xml_dict)
        #except:
        #    raise RuntimeError("Unable to write xml template")

    def _package(self):
        try:
            self._logger.info("Copying %s to %s" %
                              (self._options.disk, self._disk_dest))
            if not self._options.symlink:
                shutil.copy(self._options.disk, self._disk_dest)
            else:
                os.symlink(self._options.disk, self._disk_dest)
            if self._options.gzip:
                self._logger.info("Creating OVF Archive")
                archive = tarfile.open(self._image_name + ".ovf", "w|gz")
                archive.add(self._images_dir, arcname="images")
                archive.add(self._master_dir, arcname="master")
                archive.close()
                self._logger.info("Completed OVF Archive: %s.ovf" %
                                  os.path.join(os.getcwd(), self._image_name))
            else:
                self._logger.info("Completed Dir Structure at: %s" %
                                  self._tmp_dir)
        except:
            raise RuntimeError("Unable to complete packaging")

    def _cleanup(self):
        self._logger.info("Performing Cleanup")
        try:
            shutil.rmtree(self._tmp_dir)
        except:
            raise RuntimeError("Error cleaning up temporary directory")

    def run(self):
        try:
            self._parse_options()
            self._create_dir_structure()
            self._write_meta_template()
            self._write_ovf_template()
            if self._options.release:
                self._write_xml_template()
            self._package()
        except Exception as e:
            self._logger.exception('Error: OVF Archive Creation Failed: %s', e)
        finally:
            if self._options.gzip:
                self._cleanup()
            sys.exit(0)

if __name__ == "__main__":
    initLogger()
    creator = OVFCreator()
    creator.run()
