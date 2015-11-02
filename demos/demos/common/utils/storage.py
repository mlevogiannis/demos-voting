# File: storage.py

from __future__ import division

import io
import os
import time
import tarfile

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

from django.conf import settings
from django.core.files import File
from django.utils.encoding import filepath_to_uri
from django.utils.deconstruct import deconstructible
from django.core.files.storage import Storage, FileSystemStorage


@deconstructible
class TarFileStorage(Storage):
    
    def __init__(self, location=None, base_url=None, tar_permissions_mode=None,
        tar_file_permissions_mode=None, tar_directory_permissions_mode=None):
        
        # Absolute filesystem path to the directory that will hold tar files.
        
        if location is None:
            location = settings.TARSTORAGE_ROOT
        
        self.location = location
        
        # URL that handles the files served from TARSTORAGE_ROOT. If this is
        # None, files will not be accessible via an URL.
        
        if base_url is None:
            base_url = getattr(settings, 'TARSTORAGE_URL', None)
        
        if base_url is not None and not base_url.endswith('/'):
            base_url += '/'
        
        self.base_url = base_url
        
        # The numeric mode (i.e. 0o644) to set root tar files to.
        
        if tar_permissions_mode is None:
            tar_permissions_mode = \
                getattr(settings, 'TARSTORAGE_PERMISSIONS', None)
        
        self.tar_permissions_mode = tar_permissions_mode
        
        # The numeric mode to set files that will be added to the tar file to.
        
        if tar_file_permissions_mode is None:
            tar_file_permissions_mode = \
                getattr(settings, 'TARSTORAGE_FILE_PERMISSIONS', None)
        
        self.tar_file_permissions_mode = tar_file_permissions_mode
        
        # The numeric mode to apply to directories created in the tar file.
        
        if tar_directory_permissions_mode is None:
            tar_directory_permissions_mode = \
                getattr(settings, 'TARSTORAGE_DIRECTORY_PERMISSIONS', None)
        
        self.tar_directory_permissions_mode = tar_directory_permissions_mode
        
        # For more information about what these permission modes mean, see the
        # documentation for os.chmod(). If any of these isn't given or is None,
        # you'll get operating-system dependent behavior.
    
    def __parse_name(self, name):
        tarname, filename = name.split('/', 1)
        tarname = os.path.join(self.location, tarname) + '.tar'
        return tarname, filename
    
    def _open(self, name, mode='rb'):
        tarname, filename = self.__parse_name(name)
        tar = tarfile.open(name=tarname, mode='r')
        
        tarinfo = tar.getmember(filename)
        filebuf = io.BytesIO(tar.extractfile(tarinfo).read())
        
        return File(filebuf)
    
    def _save(self, name, content):
        tarname, filename = self.__parse_name(name)
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
        
        if hasattr(content, 'temporary_file_path'):
            fileobj = open(content.temporary_file_path(), mode='r')
        else:
            fileobj = io.BytesIO(content.read())
        
        tarinfo = tarfile.TarInfo()
        
        tarinfo.name = filename
        tarinfo.size = content.size
        tarinfo.mtime = mtime
        
        if self.tar_file_permissions_mode is not None:
            tarinfo.mode = self.tar_file_permissions_mode
        
        tar.addfile(tarinfo=tarinfo, fileobj=fileobj)
        tar.close()
        
        return name
    
    def delete(self, name):
        raise NotImplementedError('Deleting files not implemented yet.')
    
    def exists(self, name):
        tarname, filename = self.__parse_name(name)
        
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
        tarname, filename = self.__parse_name(name)
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
        tarname, filename = self.__parse_name(name)
        tar = tarfile.open(name=tarname, mode='r')
        
        tarinfo = tar.getmember(filename)
        return tarinfo.mtime


# ------------------------------------------------------------------------------

# Private storage subclasses do not use default values from the project's
# main configuration file, even when any of their given arguments is None.


@deconstructible
class PrivateFileSystemStorage(FileSystemStorage):
    
    def __init__(self, location, base_url=None, file_permissions_mode=None,
        directory_permissions_mode=None):
        
        assert location is not None
        
        super(PrivateFileSystemStorage, self).__init__(location, base_url,
            file_permissions_mode, directory_permissions_mode)
        
        if base_url is None:
            self.base_url = None
        
        if file_permissions_mode is None:
            self.file_permissions_mode = None
        
        if directory_permissions_mode is None:
            self.directory_permissions_mode = None


@deconstructible
class PrivateTarFileStorage(TarFileStorage):
    
    def __init__(self, location, base_url=None, tar_permissions_mode=None,
        tar_directory_permissions_mode=None, tar_file_permissions_mode=None):
        
        assert location is not None
        
        super(PrivateTarFileStorage, self).__init__(location, base_url,
            tar_permissions_mode, tar_file_permissions_mode,
            tar_directory_permissions_mode)
        
        if base_url is None:
            self.base_url = None
        
        if tar_permissions_mode is None:
            self.tar_permissions_mode = None
        
        if tar_file_permissions_mode is None:
            self.tar_file_permissions_mode = None
        
        if tar_directory_permissions_mode is None:
            self.tar_directory_permissions_mode = None

