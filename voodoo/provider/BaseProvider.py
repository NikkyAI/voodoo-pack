import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote

import ruamel.yaml as yaml

__all__ = ['BaseProvider']


class BaseProvider:
    """
    Provider Base class
    """
    # optional = ()
    _base_instance = None
    _required_attributes = ()
    _defaults = {}
    _typ = None

    def from_dict(self, entry: dict):
        return entry #TODO: filter out not optiona and not requires

    _conversion = {
        dict: from_dict
    }

    debug = False
    default_mc_version = None
    
    def __init__(self, *args, **kwargs):
        if type(self) is BaseProvider:
            return
        if self.debug:
            print(f'{self._typ.upper()} Provider .ctor')
        
        if not self._base_instance:
            self.instance = self.__class__.__bases__[0]()
        base_attributes = inspect.getmembers(self.instance, lambda a:not(inspect.isroutine(a)))
        base_keys = [a[0] for a in base_attributes if not(a[0].startswith('_'))]
        # base_keys = ['debug', 'default_mc_version']

        for attribute_key in base_keys:
            if attribute_key in kwargs:
                value = kwargs.get(attribute_key)
                setattr(self, attribute_key, kwargs[attribute_key])

        provider_settings = kwargs.get('provider_settings', {})
        provider_settings = provider_settings.get(self._typ, {})

        if self.debug:
            print(f'{self._typ} settings: {provider_settings}')

        attributes = inspect.getmembers(self, lambda a:not(inspect.isroutine(a)))

        attribute_keys = [a[0] for a in attributes if not(a[0].startswith('_'))]
        attribute_keys = list(set(attribute_keys) - set(base_keys))
        
        path = Path(kwargs['data_path'], 'defaults.yaml')
        if path.is_dir():
            path.rmdir()
        global_defaults = {}
        if path.exists():
            with open(path, 'r') as stream:
                try:
                    global_defaults = yaml.load(stream)
                except yaml.YAMLError as exc:
                    print(exc)
                    global_defaults = {}
        # get all default values
        global_defaults[self._typ] = {k: getattr(self, k) for k in attribute_keys}
        with open(path, 'w') as outfile:
            yaml.dump(global_defaults, outfile, default_flow_style=False)

        # write provider settings overrides to self
        for attribute_key in attribute_keys:
            if attribute_key in provider_settings:
                value = provider_settings.get(attribute_key)
                if self.debug:
                    print(f'setting {attribute_key}, value={value}')
                setattr(self, attribute_key, provider_settings[attribute_key])

    def apply_defaults(self, entry: dict):
        for key, value in self._defaults.items():
            if key not in entry:
                entry[key] = value

    def prepare_dependencies(self, entry: dict):
        pass

    def validate(self, entry: dict) -> bool:
        pass

    def resolve_dependencies(self, entry: dict, entries: List[dict]):
        pass

    def resolve_feature_dependencies(self, entry: dict, entries: List[dict], features: List[dict]):
        # check if it is a feature
        entry_name = entry.get('name')
        feature_name = entry.get('feature_name', entry_name)
        feature = next((f for f in features if f['name'] == feature_name), None)
        if 'selected' in entry and not feature:
            # find features

            # add feature
            print(entry)
            feature = {
                'name': feature_name,
                'names': [feature_name],
                'entry_refs': [
                    entry['name']
                ],
                'processed_entries': []
                #'addon_refs': [entry.get('name')]
            }
            existing = [f for f in features if entry_name in f['entry_refs']]
            for f in existing:
                print(f'TODO: DUPLICATE {f} and add {entry_name}')
            #TODO: if entry is found in other features, duplicate all and add yourself
            features.append(feature)

            self.process_feature(feature, entries, features)

    def process_feature(self, feature: dict, entries: list, features: list):
        print(f'processing {feature}')
        feature_name = feature['name']
        while(len(feature['processed_entries']) < len(feature['entry_refs'])):
            processable_entries = [e for e in feature['entry_refs'] if e not in feature['processed_entries']]
            print(f'processable: {processable_entries}')
            for entry_ref in processable_entries:
                print(f'searching {entry_ref}')
                entry = next((e for e in entries if e.get('name') == entry_ref), None)
                if not entry:
                    print(f'{entry_ref} not in entries')
                    feature['processed_entries'].append(entry_ref)
                    continue

                depends = entry.get('depends', {})
                # flatdepends = [d for _, deps in depends.items() for d in deps]
                dep_names = [d for deps in depends.values() for d in deps]
                print(f'dep_names: {dep_names}')

                # only add what is found in entries
                dep_names = [d for d in dep_names if any(d == e.get('name') for e in entries)]
                print(f'filtered dep_names: {dep_names}')
                for dep in dep_names:
                    if dep not in feature['entry_refs']:
                        feature['entry_refs'].append(dep)

                # # find all features with any intersection
                # existing = []
                # for f in features:
                #     for e in f['entry_refs']:
                #         if e in dep_names:
                #             existing.append(f)
                # print(existing)
                # for f in existing:
                #     print(f'{f} + {feature}')
                #     if any(na in feature['names'] for na in f['names']):
                #         print(f'{feature_name} tried to duplicate intersecting values')
                #         continue
                #     merged_name = f['name'] + '_' + feature['name']
                #     merged = next((fe for fe in features if fe['name'] == merged_name), None)
                #     if merged:
                #         print(f'already exists {merged}')
                #     if not merged:
                #         print(f"merging {f['names']} \n{feature['names']}\n")
                #         merged = {
                #             'name': f['name'] + '_' + feature['name'],
                #             'names': [*f['names'], *feature['names']],
                #             'entry_refs': [*f['entry_refs'], *feature['entry_refs']],
                #             'processed_entries': [*f['processed_entries'], *feature['processed_entries']],
                #         }
                #         features.append(merged)
                #     self.process_feature(merged, entries, features)
                
                feature['processed_entries'].append(entry_ref)

    def fill_information(self, entry: dict):
        if 'feature_name' not in entry and 'name' in entry and 'selected' in entry:
            entry['feature_name'] = entry['name']

    def prepare_download(self, entry: dict, cache_base: Path):
        pass

    def download(self, entry: dict, src_path: Path):
        pass

    def convert(self, entry: Any) -> dict:
        if isinstance(entry, dict):
            return entry
        conv_func = self._conversion.get(type(entry), None)
        if(conv_func):
            converted = conv_func(self, entry)
            if not converted or not isinstance(converted, dict):
                print(
                    f"failed to convert {entry} to dict, result: {type(converted)}", file=sys.stderr)
                return None
            return converted

    def match(self, entry: Any) -> bool:
        converted = self.convert(entry)
        if not converted or not isinstance(converted, dict):
            return False
        return self.__match(converted)

    def match_dict(self, entry: dict):
        # result = all (k in entry for k in self.required)
        missing = list(set(self._required_attributes) - set(entry.keys()))
        if missing:
            print(
                f"INFO: not matching {self._typ} missing from config: {missing}", file=sys.stderr)
            return False
        return True

    def __match(self, entry: dict) -> bool:
        entry_type = entry.get('type')
        if entry_type:
            if entry_type != self._typ:
                return False
            else:
                return self.match_dict(entry)
        else:
            print(
                f"WARNING {entry} is missing 'type' entry\ntrying to match anyways")
            return self.match_dict(entry)

    def resolve_path(self, entry: dict):
        package_type = entry.get('package_type') or 'mod'
        path = Path(entry.get('path') or 'mods')
        if package_type == 'loader':
            entry['path'] = 'loaders'
            entry['file_path'] = str(Path(path, entry.get(
            'file_name')))
            return
        entry['target_path'] = str(Path(path, entry.get(
            'file_name')))
        path = Path('src', path)
        if package_type == 'mod':
            side = entry.get('side') or 'both'
            if side.lower() == 'both':
                side = ''
            elif side.lower() == 'client':
                side = '_CLIENT'
            elif side.lower() == 'server':
                side = '_SERVER'
            else:
                print(f"ERROR: unknown side: {side}", file=sys.stderr)
                exit(-1)
            path = path / side
        entry['path'] = str(path)
        entry['file_path'] = str(Path(path, entry.get(
            'file_name')))

    def write_direct_url(self, entry: dict, src_path: Path):
        url = entry.get('url')
        if url:
            url = unquote(entry['url'])
            full_path = src_path / entry['file_path']
            url_path = Path(f"{full_path}.url.txt").resolve()
            url_path.parent.mkdir(parents=True, exist_ok=True)

            with open(url_path, "wb") as urlFile:
                urlFile.write(str.encode(url))
        else:
            print(f"ERROR: {entry} misses 'url'", file=sys.stderr)

    def write_feature(self, entry: dict, src_path: Path):
        if 'description' in entry and 'selected' in entry:
            full_path = src_path / entry['file_path']
            json_path = Path(f"{full_path}.info.json").resolve()
            Path(json_path.parent).mkdir(parents=True, exist_ok=True)
            feature_data = {'feature': {k: v for k, v in entry.items() if k in (
                'description', 'selected', 'recommendation', 'name')}}
            with open(json_path, 'w') as json_file:
                json.dump(feature_data, json_file)
