import os
import shutil
from pathlib import Path

from .BaseProvider import BaseProvider

__all__ = ['LocalProvider']


class LocalProvider(BaseProvider):
    """
    provieds copies of local files
    """

    # optional = ('file_name')
    _required_attributes = ('file', 'path', 'package_type')

    _typ = 'local'

    local_base = 'local'
    
    def prepare_dependencies(self, entry: dict):
        if not 'name' in entry:
            entry['name'] = Path(entry['file']).resolve().name.rstrip('.jar')
        
    def fill_information(self, entry: dict):
        if not 'file_name' in entry:
            entry['file_name'] = Path(entry['file']).resolve().name
        if not 'name' in entry:
            entry['name'] = entry['file_name'].rstrip('.jar')
        super().fill_information(entry)

    def validate(self, entry: dict) -> bool:
        # TODO: check if file exists
        return True

    def write_direct_url(self, entry: dict, src_path: Path):
        pass

    def download(self, entry: dict, pack_path: Path):
        file_path = Path(entry['file'])
        if(not os.path.isabs(file_path)):
            file_path = Path(pack_path, self.local_base, entry['file']).resolve()
        file_name = entry.get('file_name', file_path.name)
        path = Path(pack_path, entry['path']).resolve()
        path = path / file_name
        shutil.copyfile(str(file_path), str(path))
        print(f"copied {file_name}")
