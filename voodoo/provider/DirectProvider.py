from .BaseProvider import *
import requests
from pathlib import Path
import shutil

__all__ = ['DirectProvider']
class DirectProvider(BaseProvider):
    
    optional = ('file_name')
    required = ('url', 'file_name_on_disk', 'path')
    typ = 'direct'

    def __init__(self):
        super()
        print("DirectProvider .ctor")
    

    def download(self, entry: dict, src_path: Path):
        dep_cache_dir = Path(entry['cache_path']) # cache_path_curse / str(id) / str(file_id)

        file_name_on_disk = entry['file_name_on_disk']
        path = Path(src_path, entry['path']).resolve()
        download_url = entry['download_url']

        # TODO: caching
        # look for files in cache
        if dep_cache_dir.is_dir():
            # File is cached
            cached_files = [f for f in dep_cache_dir.iterdir()]
            if len(cached_files) >= 1:
                target_file = path / cached_files[0].name
                print(f"[{entry['name']} {target_file.name} (cached)")
                path.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(cached_files[0]), str(target_file))

                return

        # File is not cached and needs to be downloaded
        file_response = requests.get(download_url, stream=True)
        while file_response.is_redirect:
            source = file_response
            file_response = requests.get(source, stream=True)

        # write jarfile
        path = path / file_name_on_disk
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "wb") as mod_file:
            mod_file.write(file_response.content)

        # Try to add file to cache.
        if not dep_cache_dir.exists():
            dep_cache_dir.mkdir(parents=True)
        with open(str(dep_cache_dir / file_name_on_disk), "wb") as mod_file:
            mod_file.write(file_response.content)