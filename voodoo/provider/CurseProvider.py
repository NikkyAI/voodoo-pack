from .BaseProvider import *
from typing import Any, List, Tuple, Mapping, Dict
from ..cftypes import *
import requests
from pathlib import Path

__all__ = ['CurseProvider']


class CurseProvider(BaseProvider):

    optional = ("addon_id", "name", "mc_version", "release_type",
                "no_required", "no_optional")
    required = ()
    typ = 'curse'

    file_cache = {}

    def from_str(self, data: str):
        return {'name': data, 'type': CurseProvider.typ}

    def from_int(self, data: int):
        return {'addon_id': data, 'type': CurseProvider.typ}

    conversion = {
        str: from_str,
        int: from_int
    }

    def __init__(self, debug, download_optional, default_game_version, default_release_types):
        super()
        self.debug = debug
        self.addon_data = self.get_addon_data()
        self.download_optional = download_optional
        self.default_game_version = default_game_version
        self.default_release_types = default_release_types
        print("CurseProvider .ctor")

    def match_dict(self, entry: dict):
        # print(f"checking for name or addon_id in {entry}")
        return 'addon_id' in entry or 'name' in entry

    def prepare_dependencies(self, entry: dict) -> bool:
        # get addon_id, file_id
        param = {k: entry[k] for k in (
            'addon_id', 'name', 'mc_version', 'version', 'release_type') if k in entry}
        addon_id, file_id, file_name = self.find_file(**param)
        entry['addon_id'] = addon_id
        if file_id < 0:
            return False
        entry['file_id'] = file_id
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

            for other_entry in entries:
                if other_entry['type'] == 'curse' and other_entry['addon_id'] == dep_addon_id:
                    # dependency addon is already in the download list
                    # merge sides
                    other_side = Side.get(other_entry.get('side', 'both'))
                    side = Side.get(entry.get('side', 'both'))
                    entry['side'] = str(side | other_side)

                    provides = other_entry.get('provides', {})
                    provide_list = other_entry.get(str(dep_type), [])
                    provide_list.append(addon['name'])
                    provides[str(dep_type)] = provide_list
                    other_entry['provides'] = provides

                    break

            else:
                if dep_type == DependencyType.Required or (dep_type == DependencyType.Optional and self.download_optional):
                    dep_addon_id, dep_file_id, file_name = self.find_file (
                        addon_id=dep_addon_id, mc_version=self.default_game_version)
                    dep_addon = self.get_add_on_file(dep_addon_id, dep_file_id)
                    if dep_addon_id > 0 and dep_file_id > 0:
                        dep_addon = self.get_add_on(dep_addon_id)
                        dep_entry = {'addon_id': dep_addon_id, 'file_id': dep_file_id,
                                    'name': dep_addon['name'], 'type': 'curse', 'provides': {str(dep_type): [addon['name']]}, '_transient_dependency': True}
                        entries.append(dep_entry)
                        # depends = entry.get('depends', {})
                        # depend_list = depends.get(str(dep_type), [])
                        # depend_list.append(dep_addon['name'])
                        # depends[str(dep_type)] = depend_list
                        # entry['depends'] = depends

                        print(
                            f"added {dep_type} dependency {file_name} \nof {addon['name']}")


    def resolve_feature_dependencies(self, entry: dict, entries: List[dict]):
        # check if it is a feature
        if 'selected' in entry and 'description' in entry:
            # check if feature has a name
            if 'feature_name' not in entry:
                # feature name is not set
                entry['feature_name'] = entry['name']

        #TODO: enable and handle when writing multifile optional features into modpack.json is implemented
        # if 'feature_name' in entry: # or '_prefix' in entry:
        #     feature_name = entry['feature_name']
        #     prefix = feature_name
            
        #     depends = entry.get('depends', {})
        #     for dep_str, dep_ids in depends.items():
        #         for dep_id in dep_ids:
        #             dep_entry = next ( e for e in entries if e['addon_id'] == dep_id )
        #             self.handle_entry(prefix, feature_name, dep_entry, entries)

    # def handle_entry(self, prefix, feature_name, entry, entries):
    #     # if entry if a feaure or has a _prefix or is a dependency
    #     if ('selected' in entry ) or entry.get('_transient_dependency'):
    #         # duplicate dep_entry
    #         if not entry.get('_transient_dependency') or not '_prefix' in entry:
    #             entry = {x: entry[x] for x in entry if x not in ('selected')}
    #             entries.append(entry)
    #         entry['feature_name'] = feature_name
    #         entry['_prefix'] = prefix

    #         depends = entry.get('depends', {})
    #         for dep_str, dep_ids in depends.items():
    #             for dep_id in dep_ids:
    #                 print(f'seaching for id: {dep_id}')
    #                 dep_entry = next ( e for e in entries if e['addon_id'] == dep_id )
    #                 self.handle_entry(prefix, feature_name, dep_entry, entries)


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
            entry['file_name'] = addon_file['fileName']

        if 'file_name_on_disk' not in entry:
            entry['file_name_on_disk'] = addon_file['fileNameOnDisk']

        if 'download_url' not in entry:
            entry['download_url'] = addon_file['downloadURL']

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
    
    def prepare_download(self, entry: dict, cache_base: Path):
        entry['type'] = 'direct'
        if 'file_name_on_disk' not in entry:
            entry['file_name_on_disk'] = entry['file_name']
        
        if 'cache_base' not in entry:
            entry['cache_base'] = str(cache_base)
        if 'cache_path' not in entry:
            entry['cache_path'] = str(Path(entry['cache_base'], str(entry['addon_id']), str(entry['file_id'])))

    def get_addon_data(self) -> List[Mapping[str, Any]]:
        if self.debug:
            print(
                f'get https://cursemeta.nikky.moe/api/addon/?mods=1&property=id,name,summary,websiteURL,packageType,categorySection.path')
        req = requests.get(
            f'https://cursemeta.nikky.moe/api/addon/?mods=1&property=id,name,summary,websiteURL,packageType,categorySection.path')
        req.raise_for_status()
        if req.status_code == 200:
            addon_data = req.json()
            return addon_data
        return None

    def get_add_on(self, addon_id: int) -> Dict[str, Any]:
        addon_files = self.file_cache.get(id, None)
        if not addon_files:
            self.file_cache[id] = {}
        addon = next(a for a in self.addon_data if a['id'] == addon_id)
        return addon
        if self.debug:
            print(f'get https://cursemeta.nikky.moe/api/addon/{addon_id}')
        req = requests.get(f'https://cursemeta.nikky.moe/api/addon/{addon_id}')
        req.raise_for_status()
        if req.status_code == 200:
            addon = req.json()
            return addon

    def get_add_on_file(self, addon_id: int, file_id: int) -> Dict[str, Any]:
        addon_files = self.file_cache.get(id, None)
        if addon_files:
            file = addon_files.get(file_id, None)
            if file:
                return file

        if self.debug:
            print(
                f'get https://cursemeta.nikky.moe/api/addon/{addon_id}/files/{file_id}')
        req = requests.get(
            f'https://cursemeta.nikky.moe/api/addon/{addon_id}/files/{file_id}'
        )
        req.raise_for_status()
        if req.status_code == 200:
            files = req.json()
            addon_files[file_id] = files

            return file

    def get_add_on_all_files(self, addon_id: int) -> List[Dict[str, Any]]:
        addon_files = self.file_cache.get(id, None)
        if not addon_files:
            self.file_cache[id] = {}
            addon_files = self.file_cache.get(id, None)
        if self.debug:
            print(
                f'get https://cursemeta.nikky.moe/api/addon/{addon_id}/files')
        req = requests.get(
            f'https://cursemeta.nikky.moe/api/addon/{addon_id}/files'
        )
        req.raise_for_status()
        if req.status_code == 200:
            files = req.json()
            for file in files:
                addon_files[file['id']] = file
            return files

    # TODO: refactor these
    defaultGameVersion = "1.10.2"

    def find_file(self, mc_version: str = None,
                  name: str = None,
                  version: str = None,
                  release_type: List[Any] = None,
                  addon_id: int = None
                ) -> Tuple[int, int, str]:

        if not release_type:
            release_type = self.default_release_types
        release_type = list(release_type)
        release_type = [RLType.get(t) for t in release_type]
        if not mc_version:
            mc_version = self.default_game_version

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
                 and mc_version in f['gameVersion']
                 and RLType.get(f['releaseType']) in release_type]
        if files:
            # sort by date
            files.sort(key=lambda x: x['fileDate'], reverse=True)
            # print('addon_files')
            # for f in files:
            #     print(f)
            file = files[0]
            return addon_id, file['id'], file['fileName']  # , description

        print(addon)
        print(
            f"no matching version found for: {addon['name']} addon url: {addon['websiteURL']} mc_version: {mc_version} version: {version} ")
        return addon_id, -1, ''
