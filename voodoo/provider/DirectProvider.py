import shutil
from pathlib import Path

import requests

from urllib.parse import urlparse

from .BaseProvider import BaseProvider

__all__ = ['DirectProvider']


class DirectProvider(BaseProvider):
    """
    Donloads files form urls directly
    """
    # optional = ('file_name',)
    _required_attributes = ('url', 'path', 'package_type')
    _typ = 'direct'

    def validate(self, entry: dict) -> bool:
        return True

    def fill_information(self, entry: dict):
        url = entry['url']
        parsed = urlparse(url)
        url_path = Path(parsed.netloc, parsed.path.lstrip('/'))
        if 'file_name' not in entry:
            entry['file_name'] = url_path.name
        if 'name' not in entry:
            entry['name'] = entry['file_name'].rsplit('.', 1)[0]

    def prepare_download(self, entry: dict, cache_base: Path):
        url = entry['url']
        parsed = urlparse(url)
        url_path = Path(parsed.netloc, parsed.path.lstrip('/'))
        if 'file_name' not in entry:
            entry['file_name'] = url_path.name
        if 'cache_base' not in entry:
            entry['cache_base'] = str(cache_base)
        if 'cache_path' not in entry:
            cache_path = Path(entry['cache_base'], url_path.parent)
            entry['cache_path'] = str(cache_path)

    def download(self, entry: dict, pack_path: Path):
        url = entry['url']
        if self.debug:
            print(f'downloading {url}')
        dep_cache_dir = Path(entry['cache_path'])

        file_name = entry['file_name']
        file_path = Path(pack_path, entry['file_path'])
        Path(file_path.parent).mkdir(parents=True, exist_ok=True)
        url = entry['url']

        # look for files in cache
        if dep_cache_dir.is_dir():
            # File is cached
            cached_files = [f for f in dep_cache_dir.iterdir()]
            if cached_files:
                print(f"[{entry['name']}] {cached_files[0].name} (cached)")
                shutil.copyfile(str(cached_files[0]), str(file_path))
                return

        # File is not cached and needs to be downloaded
        file_response = requests.get(url, stream=True)
        while file_response.is_redirect:
            source = file_response
            file_response = requests.get(source, stream=True)

        # write jarfile
        with open(file_path, "wb") as mod_file:
            mod_file.write(file_response.content)

        print(f"[{entry['name']}] {file_name} (downloaded)")

        # Try to add file to cache.
        if not dep_cache_dir.exists():
            dep_cache_dir.mkdir(parents=True)
        with open(str(dep_cache_dir / file_name), "wb") as mod_file:
            mod_file.write(file_response.content)
