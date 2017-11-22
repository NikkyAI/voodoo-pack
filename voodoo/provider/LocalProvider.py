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
    required_attributes = ('file')

    typ = 'local'

    local_base = 'local'

    def fill_information(self, entry: dict):
        if not 'name' in entry:
            entry['name'] = Path(entry['file']).resolve().name.rstrip('.jar')
        if not 'file_name' in entry:
            entry['file_name'] = Path(entry['file']).resolve().name
        super().fill_information(entry)

    def validate(self, entry: dict) -> bool:
        # TODO: check if file exists
        return True

    def write_direct_url(self, entry: dict, src_path: Path):
        pass

    def download(self, entry: dict, src_path: Path):  # TODO: add
        file_src = Path(entry['file'])
        if(not os.path.isabs(file_src)):
            file_src = Path(self.local_base, entry['file'])
        file_name = entry.get('file_name', file_src.name)
        path = Path(src_path, entry['path']).resolve()
        path = path / file_name
        shutil.copyfile(str(file_src), str(path))
        print(f"copied {file_name}")
