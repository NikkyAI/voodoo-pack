from itertools import groupby
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import requests
import yaml

from ..cftypes import *
from .BaseProvider import BaseProvider

__all__ = ['CurseProvider']


class CurseProvider(BaseProvider):
    """
    Gets mods and their dependencies from curse
    """

    # optional = ("addon_id", "name", "mc_version", "release_type", "no_required", "no_optional")
    _required_attributes = ()
    _typ = 'curse'

    __file_cache = {}

    def from_str(self, data: str):
        return {'name': data, 'type': self._typ}

    def from_int(self, data: int):
        return {'addon_id': data, 'type': self._typ}

    _conversion = {
        str: from_str,
        int: from_int
    }

    optional = False
    release_types = [str(RLType.Release), str(RLType.Beta)]
    meta_url: str = 'https://cursemeta.nikky.moe'
    dump_data = True

    def __init__(self, *args, **kwargs):  # optional, default_release_types,
        super().__init__(*args, **kwargs)

        data_path = kwargs['data_path']
        self.addon_data = self.get_addon_data()
        if self.dump_data:
            key = 'categorySection.name'
            for addon_type, addons in groupby(sorted(self.addon_data, key=lambda k: k[key]), lambda d: d[key]):
                path = Path(data_path, 'addons', f'{addon_type}.yaml')
                addon_data = dict()
                for addon in addons:
                    website_url = addon['websiteURL']
                    addon_id = addon['id']
                    api_url = f'{self.meta_url}/api/addon/{addon_id}'
                    addon_data[addon['name']] = {
                        'webste_url': website_url, 'api_url': api_url}
                Path(path.parent).mkdir(parents=True, exist_ok=True)
                with open(path, 'w') as outfile:
                    yaml.dump(addon_data, outfile, default_flow_style=False)

    def match_dict(self, entry: dict):
        # print(f"checking for name or addon_id in {entry}")
        return 'addon_id' in entry or 'name' in entry

    def prepare_dependencies(self, entry: dict):
        # get addon_id, file_id
        param = {k: entry[k] for k in (
            'addon_id', 'name', 'mc_version', 'version', 'release_types') if k in entry}
        addon_id, file_id, file_name = self.find_file(**param)
        entry['addon_id'] = addon_id
        entry['file_id'] = file_id
        if 'file_name' not in entry:
            entry['file_name'] = file_name

    def validate(self, entry: dict) -> bool:
        file_id = entry.get('file_id')
        if not file_id or file_id < 0:
            return False
        return True

    def resolve_dependencies(self, entry: dict, entries: List[dict]):
        # returns multiple values
        addon_id = entry['addon_id']
        file_id = entry['file_id']
        addon = self.get_add_on(addon_id)

        addon_file = self.get_add_on_file(addon_id, file_id)

        for dependency in addon_file['dependencies']:
            dep_type = DependencyType.get(dependency['type'])
            dep_addon_id = dependency['addOnId']

            dep_addon = self.get_add_on(dep_addon_id)

            depends = entry.get('depends', {})
            depend_list = depends.get(str(dep_type), [])
            depend_list.append(dep_addon['name'])
            depends[str(dep_type)] = depend_list
            entry['depends'] = depends

            # find duplicat entry
            dep_entry = next((e for e in entries if (e['type'] == 'curse' and e.get(
                'addon_id') == dep_addon_id) or e.get('name') == dep_addon['name']), None)
            if not dep_entry:
                if dep_type == DependencyType.Required or (dep_type == DependencyType.Optional and entry.get('optional')):
                    dep_addon_id, dep_file_id, file_name = self.find_file(
                        addon_id=dep_addon_id, mc_version=self.default_mc_version)
                    assert dep_addon_id > 0 and dep_file_id > 0, f"dependency resolution error for {dep_type} dependency {dep_addon['name']} {dep_addon['id']} of {addon['name']} {addon['id']}"
                    if dep_addon_id > 0 and dep_file_id > 0:
                        dep_addon = self.get_add_on(dep_addon_id)
                        dep_entry = {
                            'addon_id': dep_addon_id,
                            'file_id': dep_file_id,
                            'name': dep_addon['name'],
                            'type': 'curse',
                            # 'provides': {str(dep_type): [addon['name']]}, # added by second step
                        }
                        entries.append(dep_entry)

                        print(
                            f"added {dep_type} dependency {file_name} \nof {addon['name']}")

            if dep_entry:
                # merge sides
                other_side = Side.get(dep_entry.get('side', 'both'))
                side = Side.get(entry.get('side', 'both'))
                entry['side'] = str(side | other_side)

                provides = dep_entry.get('provides', {})
                provide_list = dep_entry.get(str(dep_type), [])
                provide_list.append(addon['name'])
                provides[str(dep_type)] = provide_list
                dep_entry['provides'] = provides

    def fill_information(self, entry: dict):
        addon_id = entry['addon_id']
        file_id = entry['file_id']
        addon = self.get_add_on(addon_id)
        addon_file = self.get_add_on_file(addon_id, file_id)
        if 'name' not in entry:
            entry['name'] = addon['name']

        if 'description' not in entry:
            entry['description'] = addon['summary']

        if 'file_name' not in entry:
            entry['file_name'] = addon_file['fileNameOnDisk']

        if 'url' not in entry:
            entry['url'] = addon_file['downloadURL']

        if 'websited_url' not in entry:
            entry['websited_url'] = addon['websiteURL']

        if 'package_type' not in entry:
            entry['package_type'] = addon['packageType']

        if 'path' not in entry:
            entry['path'] = addon['categorySection.path']

        provides = entry.get('provides', {})
        for release_type in provides.keys():
            provide_list = provides[release_type]
            new_list = []
            for provider in provide_list:
                if isinstance(provider, int):
                    provide_addon = self.get_add_on(provider)
                    new_list.append(provide_addon['name'])
            provides[str(release_type)] = new_list
        entry['provides'] = provides
        super().fill_information(entry)

    def prepare_download(self, entry: dict, cache_base: Path):
        entry['type'] = 'direct'

        if 'cache_base' not in entry:
            entry['cache_base'] = str(cache_base)
        if 'cache_path' not in entry:
            entry['cache_path'] = str(Path(entry['cache_base'], str(
                entry['addon_id']), str(entry['file_id'])))

    def get_addon_data(self) -> List[Mapping[str, Any]]:
        if self.debug:
            print(
                f'get {self.meta_url}/api/addon/?mods=1&property=id,name,summary,websiteURL,packageType,categorySection.name,categorySection.path')
        req = requests.get(
            f'{self.meta_url}/api/addon/?mods=1&texturepacks=1&worlds=1&property=id,name,summary,websiteURL,packageType,categorySection.name,categorySection.path')
        req.raise_for_status()
        if req.status_code == 200:
            addon_data = req.json()
            return addon_data
        return None

    def get_add_on(self, addon_id: int) -> Dict[str, Any]:
        addon_files = self.__file_cache.get(id, None)
        if not addon_files:
            self.__file_cache[id] = {}
        addon = next(a for a in self.addon_data if a['id'] == addon_id)
        return addon
        if self.debug:
            print(f'get {self.meta_url}/api/addon/{addon_id}')
        req = requests.get(f'{self.meta_url}/api/addon/{addon_id}')
        req.raise_for_status()
        if req.status_code == 200:
            addon = req.json()
            return addon

    def get_add_on_file(self, addon_id: int, file_id: int) -> Dict[str, Any]:
        addon_files = self.__file_cache.get(id, None)
        if addon_files:
            file = addon_files.get(file_id, None)
            if file:
                return file

        if self.debug:
            print(
                f'get {self.meta_url}/api/addon/{addon_id}/files/{file_id}')
        req = requests.get(
            f'{self.meta_url}/api/addon/{addon_id}/files/{file_id}'
        )
        req.raise_for_status()
        if req.status_code == 200:
            files = req.json()
            addon_files[file_id] = files

            return file

    def get_add_on_all_files(self, addon_id: int) -> List[Dict[str, Any]]:
        addon_files = self.__file_cache.get(id, None)
        if not addon_files:
            self.__file_cache[id] = {}
            addon_files = self.__file_cache.get(id, None)
        if self.debug:
            print(
                f'get {self.meta_url}/api/addon/{addon_id}/files')
        req = requests.get(
            f'{self.meta_url}/api/addon/{addon_id}/files'
        )
        req.raise_for_status()
        if req.status_code == 200:
            files = req.json()
            for file in files:
                addon_files[file['id']] = file
            return files

    def find_file(self, mc_version: List[str] = None,
                  name: str = None,
                  version: str = None,
                  release_types: List[Any] = None,
                  addon_id: int = None
                  ) -> Tuple[int, int, str]:

        if not release_types:
            release_types = self.release_types
        release_types = list(release_types)
        release_types = [RLType.get(t) for t in release_types]
        if not mc_version:
            mc_version = self.default_mc_version
        mc_version = list(mc_version)

        addon = {}

        found = False
        for addon in self.addon_data:
            if (name and name == addon['name']) or (addon_id and addon_id == addon['id']):
                found = True
                break

        # process addon
        if not found:
            print(name or str(addon_id) + ' not found')
            return -1, -1, None

        addon_id = addon["id"]

        #description = get_add_on_description(id)

        files = self.get_add_on_all_files(addon_id)
        # TODO improve and add version detection
        # ModVersion in f['file_name']
        files = [f for f in files
                 if version and version in f['fileName'] or not version
                 and any(version in mc_version for version in f['gameVersion'])
                 and RLType.get(f['releaseType']) in release_types]
        if files:
            # sort by date
            files.sort(key=lambda x: x['fileDate'], reverse=True)
            # print('addon_files')
            # for f in files:
            #     print(f)
            file = files[0]
            # , description
            return addon_id, file['id'], file['fileNameOnDisk']

        print(addon)
        print(
            f"no matching version found for: {addon['name']} addon url: {addon['websiteURL']} mc_version: {mc_version} version: {version} ")
        return addon_id, -1, ''
