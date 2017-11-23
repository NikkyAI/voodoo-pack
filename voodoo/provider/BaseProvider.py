import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote

import yaml

__all__ = ['BaseProvider']


class BaseProvider:
    """
    Provider Base class
    """
    # optional = ()
    required_attributes = ()
    defaults = {}
    typ = None

    def from_dict(self, entry: dict):
        return entry #TODO: filter out not optiona and not requires

    conversion = {
        dict: from_dict
    }

    debug = False
    default_mc_version = None
    
    def __init__(self, *args, **kwargs):
        if type(self) is BaseProvider:
            return
        if self.debug:
            print(f'{self.typ.upper()} Provider .ctor')
        attribute_keys = ['debug', 'default_mc_version']
        for attribute_key in attribute_keys:
            if attribute_key in kwargs:
                value = kwargs.get(attribute_key)
                setattr(self, attribute_key, kwargs[attribute_key])

        provider_settings = kwargs.get('provider_settings', {})
        provider_settings = provider_settings.get(self.typ, {})

        if self.debug:
            print(f'{self.typ} settings: {provider_settings}')

        attributes = inspect.getmembers(self, lambda a:not(inspect.isroutine(a)))
        base_attributes = inspect.getmembers(self.__class__.__bases__[0](), lambda a:not(inspect.isroutine(a)))
        attribute_keys = [a[0] for a in attributes if not(a[0].startswith('_'))]
        base_keys = [a[0] for a in base_attributes if not(a[0].startswith('_'))]
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
        global_defaults[self.typ] = {k: getattr(self, k) for k in attribute_keys}
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
        for key, value in self.defaults.items():
            if key not in entry:
                entry[key] = value

    def prepare_dependencies(self, entry: dict):
        pass

    def validate(self, entry: dict) -> bool:
        pass

    def resolve_dependencies(self, entry: dict, entries: List[dict]):
        pass

    def resolve_feature_dependencies(self, entry: dict, entries: List[dict]):
        pass

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
        conv_func = self.conversion.get(type(entry), None)
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
        missing = list(set(self.required_attributes) - set(entry.keys()))
        if missing:
            print(
                f"INFO: not matching {self.typ} missing from config: {missing}", file=sys.stderr)
            return False
        return True

    def __match(self, entry: dict) -> bool:
        entry_type = entry.get('type')
        if entry_type:
            if entry_type != self.typ:
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
            json_path.parent.mkdir(parents=True, exist_ok=True)
            feature_data = {'feature': {k: v for k, v in entry.items() if k in (
                'description', 'selected', 'recommendation', 'name')}}
            with open(json_path, 'w') as json_file:
                json.dump(feature_data, json_file)
