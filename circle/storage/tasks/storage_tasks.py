# Copyright 2014 Budapest University of Technology and Economics (BME IK)
#
# This file is part of CIRCLE Cloud.
#
# CIRCLE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# CIRCLE is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with CIRCLE.  If not, see <http://www.gnu.org/licenses/>.

from manager.mancelery import celery


@celery.task(name='storagedriver.list')
def list(data_store_type, dir):
    pass


@celery.task(name='storagedriver.list_files')
def list_files(data_store_type, dir):
    pass


@celery.task(name='storagedriver.create')
def create(disk_desc):
    pass


@celery.task(name='storagedriver.download')
def download(disk_desc, url):
    pass


@celery.task(name='storagedriver.delete')
def delete(disk_desc):
    pass


@celery.task(name='storagedriver.delete_dump')
def delete_dump(data_store_type, dir, filename):
    pass


@celery.task(name='storagedriver.snapshot')
def snapshot(disk_desc):
    pass


@celery.task(name='storagedriver.get')
def get(disk_desc):
    pass


@celery.task(name='storagedriver.merge')
def merge(src_disk_desc, dst_disk_desc):
    pass


@celery.task(name='storagedriver.is_exists')
def is_exists(data_store_type, path, disk_name):
    pass


@celery.task(name='storagedriver.make_free_space')
def make_free_space(datastore, path, deletable_disks, percent):
    pass


@celery.task(name='storagedriver.get_storage_stat')
def get_storage_stat(data_store_type, path):
    pass
