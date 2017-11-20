import os
import shutil
from pathlib import Path

from .BaseProvider import BaseProvider

__all__ = ['LocalProvider']


class LocalProvider(BaseProvider):

    optional = ('file_name_on_disk')
    required = ('file', 'path')
    typ = 'local'

    def __init__(self, local_base: Path):
        super()
        self.local_base = local_base
        print("LocalProvider .ctor")

    def fill_information(self, entry: dict):
        if not 'name' in entry:
            entry['name'] = Path(entry['file']).resolve().name.rstrip('.jar')
        if not 'file_name' in entry:
            entry['file_name'] = Path(entry['file']).resolve().name
        if not 'file_name_on_disk' in entry:
            entry['file_name_on_disk'] = Path(entry['file']).resolve().name
        super().fill_information(entry)

    def prepare_dependencies(self, entry: dict) -> bool:
        return True

    def write_direct_url(self, entry: dict, src_path: Path):
        pass

    def download(self, entry: dict, src_path: Path):  # TODO: add
        file_src = Path(entry['file'])
        if(not os.path.isabs(file_src)):
            file_src = Path(self.local_base, entry['file'])
        file_name_on_disk = entry.get('file_name_on_disk', file_src.name)
        path = Path(src_path, entry['path']).resolve()
        path = path / file_name_on_disk
        shutil.copyfile(str(file_src), str(path))
        print(f"copied {file_name_on_disk}")
