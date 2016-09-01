# File: storage.py

from __future__ import absolute_import, division, print_function, unicode_literals

import datetime
import os
import tarfile
import time

from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri
from django.utils.six.moves.urllib.parse import urljoin


@deconstructible
class FileSystemStorage(FileSystemStorage):
    
    def __init__(self, location, base_url=None, file_permissions_mode=None, directory_permissions_mode=None):
        
        assert location is not None
        super(FileSystemStorage, self).__init__(location, base_url, file_permissions_mode, directory_permissions_mode)
        
        # Ignore default values from the project's main configuration file,
        # even if the given arguments are None.
        
        if base_url is None:
            self.base_url = None
        
        if file_permissions_mode is None:
            self.file_permissions_mode = None
        
        if directory_permissions_mode is None:
            self.directory_permissions_mode = None


@deconstructible
class TarFileStorage(Storage):
    
    def __init__(self, location, base_url=None, tar_permissions_mode=None,
                 tar_file_permissions_mode=None, tar_directory_permissions_mode=None):
        
        # Absolute filesystem path to the directory that will hold tar files.
        
        self.location = location
        
        # URL that handles the files served from location. If this is None,
        # files will not be accessible via an URL.
        
        if base_url is not None and not base_url.endswith('/'):
            base_url += '/'
        
        self.base_url = base_url
        
        # The numeric mode (i.e. 0o644) to set root tar files to.
        
        self.tar_permissions_mode = tar_permissions_mode
        
        # The numeric mode (i.e. 0o644) to set tar member files to.
        
        self.tar_file_permissions_mode = tar_file_permissions_mode
        
        # The numeric mode (i.e. 0o644) to set tar member directories to.
        
        self.tar_directory_permissions_mode = tar_directory_permissions_mode
        
        # For more information about what these permission modes mean, see
        # the documentation for os.chmod(). If any of these is not given or
        # is None, you'll get operating-system dependent behavior.
    
    def _get_tar_name(self, name):
        assert '/' in name
        return os.path.join(self.location, name.split('/', 1)[0]) + '.tar'
    
    def _get_file_name(self, name):
        assert '/' in name
        return name.split('/', 1)[1]
    
    def _open(self, name, mode='rb'):
        
        tarname = self._get_tar_name(name)
        filename = self._get_file_name(name)
        
        tar = tarfile.open(name=tarname, mode='r')
        tarinfo = tar.getmember(filename)
        
        filebuf = File(tar.extractfile(tarinfo), name=tarinfo.name)
        filebuf.mtime = tarinfo.mtime
        
        return filebuf
    
    def _save(self, name, content):
        
        if not os.path.isdir(self.location):
            os.makedirs(self.location)
        
        tarname = self._get_tar_name(name)
        filename = self._get_file_name(name)
        
        tar = tarfile.open(name=tarname, mode='a')
        
        if self.tar_permissions_mode is not None:
            os.chmod(tarname, self.tar_permissions_mode)
        
        mtime = time.time()
        
        if self.tar_directory_permissions_mode is not None:
            
            dirpath = ''
            
            for dirname in filename.split('/')[:-1]:
                
                dirpath += dirname + '/'
                tarinfo = tarfile.TarInfo()
                
                tarinfo.name = dirpath
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.mtime = mtime
                tarinfo.mode = self.tar_directory_permissions_mode
                
                tar.addfile(tarinfo=tarinfo)
        
        tarinfo = tarfile.TarInfo()
        
        tarinfo.name = filename
        tarinfo.size = content.size
        tarinfo.mtime = mtime
        
        if self.tar_file_permissions_mode is not None:
            tarinfo.mode = self.tar_file_permissions_mode
        
        tar.addfile(tarinfo=tarinfo, fileobj=content)
        tar.close()
        
        return name
    
    def delete(self, name):
        raise NotImplementedError('Deleting files not implemented yet.')
    
    def exists(self, name):
        
        tarname = self._get_tar_name(name)
        filename = self._get_file_name(name)
        
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
        
        tarname = self._get_tar_name(name)
        filename = self._get_file_name(name)
        
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
        
        tarname = self._get_tar_name(name)
        filename = self._get_file_name(name)
        
        tar = tarfile.open(name=tarname, mode='r')
        tarinfo = tar.getmember(filename)
        
        return datetime.datetime.fromtimestamp(tarinfo.mtime)

