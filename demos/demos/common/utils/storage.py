# File: storage.py

import os
import time
import tarfile

from io import BytesIO
from urllib.parse import urljoin

from django.core.files import File
from django.utils.encoding import filepath_to_uri
from django.utils.deconstruct import deconstructible
from django.core.files.storage import Storage

from demos.common.utils import config


@deconstructible
class TarFileStorage(Storage):
	
	def __init__(self, location=None, base_url=None, tar_permissions_mode=None):
		
		if location is None:
			location = config.TARSTORAGE_ROOT
		self.location = location
		
		if base_url is None:
			base_url = config.TARSTORAGE_URL
		if base_url is not None and not base_url.endswith('/'):
			base_url += '/'
		self.base_url = base_url
		
		if tar_permissions_mode is None:
			tar_permissions_mode = config.TARSTORAGE_PERMISSIONS
		self.tar_permissions_mode = tar_permissions_mode
	
	def _name_split(self, name):
		tarname, filename = name.split('/', maxsplit=1)
		tarname = os.path.join(self.location, tarname) + '.tar'
		return tarname, filename
	
	def _open(self, name, mode='rb'):
		tarname, filename = self._name_split(name)
		tar = tarfile.open(name=tarname, mode='r')
		
		tarinfo = tar.getmember(filename)
		filebuf = BytesIO(tar.extractfile(tarinfo).read())
		
		return File(filebuf)
	
	def _save(self, name, content):
		tarname, filename = self._name_split(name)
		tar = tarfile.open(name=tarname, mode='a')
		
		if self.tar_permissions_mode is not None:
			os.chmod(tarname, self.tar_permissions_mode)
		
		if hasattr(content, 'temporary_file_path'):
			fileobj = open(content.temporary_file_path(), mode='r')
		else:
			fileobj = BytesIO(content.read())
		
		tarinfo = tarfile.TarInfo()
		
		tarinfo.name = filename
		tarinfo.size = content.size
		tarinfo.mtime = time.time()
		
		tar.addfile(tarinfo=tarinfo, fileobj=fileobj)
		tar.close()
		
		return name
	
	def delete(self, name):
		raise NotImplementedError('Deleting files not implemented yet.')
	
	def exists(self, name):
		tarname, filename = self._name_split(name)
		
		if not os.path.isfile(tarname):
			return False
		
		try:
			tar = tarfile.open(name=tarname, mode='r')
		except (tarfile.ReadError, tarfile.CompressionError):
			return False
		
		try:
			tarinfo = tar.getmember(filename)
		except KeyError:
			return False
		
		return True
	
	def listdir(self, path):
		raise NotImplementedError('Listing contents not implemented yet.')
	
	def size(self, name):
		tarname, filename = self._name_split(name)
		tar = tarfile.open(name=tarname, mode='r')
		
		tarinfo = tar.getmember(filename)
		return tarinfo.size
	
	def url(self, name):
		if self.base_url is None:
			raise ValueError("This file is not accessible via a URL.")
		return urljoin(self.base_url, filepath_to_uri(name))
	
	def accessed_time(self, name):
		raise NotImplementedError('Access time is not supported.')
	
	def created_time(self, name):
		raise NotImplementedError('Creation time is not supported.')
	
	def modified_time(self, name):
		tarname, filename = self._name_split(name)
		tar = tarfile.open(name=tarname, mode='r')
		
		tarinfo = tar.getmember(filename)
		return tarinfo.mtime

