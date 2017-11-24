#!/bin/python3
# -*- coding: utf-8 -*-
import argparse
import io
import sys
import traceback
from itertools import groupby
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, List, Tuple

import appdirs
import requests
import simplejson as json
import yaml

from .cftypes import DependencyType, RLType
from .dependency_graph import generate_graph
from .loader import Loader
from .provider import *


def main():  # TODO: move to __main__
    parser = argparse.ArgumentParser(
        description='Download mods from curseforge and other sources')
    parser.add_argument('packs', nargs='*', default=[], help='packs')
    parser.add_argument(
        '-c', '--config', default='config/config.yaml', help='config file')
    # parser.add_argument('--auth', help='auth file for github login')
    # parser.add_argument('--username_github', help='github login')
    # parser.add_argument('--password_github', help='github password')
    parser.add_argument('--debug', dest='debug',
                        action='store_true', help='display debug info')
    args, unknown = parser.parse_known_args()
    args = vars(args)

    voodoo = Voodoo(**args)
    voodoo.process_packs()


class Voodoo:
    forge_data = None

    def __init__(self, config, debug, packs):
        self.debug = debug
        if self.debug:
            print('using encoding {}'.format(sys.stdout.encoding))
        self.config_path = Path(config).resolve()
        self.packs = packs

        self.cache_dir = appdirs.AppDirs(
            appname='voodoo', appauthor='nikky').user_cache_dir

        # parse config
        config_dir = self.config_path.parent
        self.global_config = {}

        config_suffix = self.config_path.suffix
        if config_suffix == '.yaml':
            default_config_path = config_dir / 'default.yaml'
            config_dir.mkdir(parents=True, exist_ok=True)
            output = io.StringIO()
            with open(default_config_path) as infile:
                output.write(infile.read())
            output.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(self.config_path) as infile:
                output.write(infile.read())
            self.config_str = output.getvalue()
            output.close()

            self.global_config = yaml.load(self.config_str, Loader)
            if self.debug:
                print(yaml.dump(self.global_config))
            self.config_path = config_dir
            temp_path = self.global_config.get('temp_path')
            if temp_path:
                temp_path = Path(self.config_path, temp_path)
                temp_path.mkdir(parents=True, exist_ok=True)
                temp_path = Path(temp_path, 'generated_config.yaml')
                with open(temp_path, 'w') as outfile:
                    outfile.write(self.config_str)
        else:
            print('requires yaml config file')
            exit(-1)

        # auth_file = args.auth or config.get('authentication', None)
        # auth = config.get('authentication', {})
        # if args.username_github and args.password_github:
        #     auth_github = {'username': args.username, 'password': args.password}
        #     auth['github'] = auth_github

    def process_packs(self):
        if self.packs:
            for pack in self.packs:
                meta_config = self.global_config['modpacks'].get(pack, {})
                self.process_pack(
                    pack_base=pack, meta_config=meta_config, disable_skip=True)
        else:
            for pack, meta_config in self.global_config['modpacks'].items():
                self.process_pack(pack_base=pack, meta_config=meta_config)

    def process_pack(self, pack_base: str, meta_config: dict = {}, disable_skip: bool = False):
        if not meta_config.get('enabled', True) and not disable_skip:
            print(f'skipped {pack_base}')
            return
        else:
            print(f'processing {pack_base}')

        pack_config_base = Path(
            self.config_path, self.global_config.get('packs'))
        pack_config_path = pack_config_base / f'{pack_base}.yaml'

        output = io.StringIO()
        output.write(self.config_str)
        output.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
        with open(pack_config_path) as infile:
            output.write(infile.read())
        config_str = output.getvalue()
        output.close()
        try:
            pack_config = yaml.load(config_str, Loader)
        except yaml.YAMLError as exc:
            print('failed loading yaml')
            temp_path = Path(self.config_path, 'fail')
            temp_path.mkdir(parents=True, exist_ok=True)
            temp_path = temp_path / f'{pack_base}.yaml'
            with open(temp_path, 'w') as outfile:
                outfile.write(config_str)
            print(
                f'written failing yaml to {temp_path} \nfailed parsing config {exc}')
            exit(-1)
        # apply config overrides
        pack_config == {**pack_config, **meta_config}

        temp_path = pack_config.get('temp_path')
        if temp_path:
            temp_path = Path(self.config_path, temp_path)
            temp_path.mkdir(parents=True, exist_ok=True)
            merged_config_path = temp_path / f'{pack_base}.yaml'
            with open(merged_config_path, 'w') as outfile:
                outfile.write(config_str)

        output_path = Path(pack_config.get('output') or 'modpacks', pack_base)
        data_path = Path(pack_config.get('data_path', 'data'))
        assert not data_path.is_absolute(), 'data_path has to be relative to the output path'
        data_path = Path(output_path, data_path)
        data_path.mkdir(parents=True, exist_ok=True)
        if self.debug:
            print(yaml.dump(pack_config))
        urls = pack_config.get('urls', True)
        pack_name = pack_config.get('name' or pack_base)
        mc_version = pack_config.get('mc_version')
        if not isinstance(mc_version, list):
            mc_version = [mc_version]
        mc_version = [str(v) for v in mc_version]
        assert mc_version, 'no Minecraft version defined'
        forge_version = pack_config.get('forge')
        assert forge_version, 'no Forge version defined'

        provider_settings = pack_config.get('provider_settings', {})
        provider_args = {'debug': self.debug, 'output_path': output_path, 'data_path': data_path,
                         'default_mc_version': mc_version, 'provider_settings': provider_settings}

        print('initializing providers')

        providers: List[BaseProvider] = []
        providers.append(CurseProvider(**provider_args))
        providers.append(DirectProvider(**provider_args))
        providers.append(LocalProvider(**provider_args))
        providers.append(MavenProvider(**provider_args))
        providers.append(GithubProvider(**provider_args))
        providers.append(JenkinsProvider(**provider_args))

        print(f'output path {output_path}')
        mods = pack_config.get('mods', [])

        provider_map = {p._typ: p for p in providers}

        def find_matching(mod: Any) -> BaseProvider:
            for provider in providers:
                if provider.match(mod):
                    return provider
            return None

        def assert_dict(check_name: str, keys: Tuple[str], entries: List[dict]):
            fail = False
            all_missing = {}
            for entry in entries:
                missing = set(keys) - set(entry.keys())
                if missing:
                    print(
                        f"[{check_name}] missing {', '.join(missing)} from \n\t{entry}", file=sys.stderr)
                    fail = True
                    entry_id = entry.get('name') or entry.get(
                        'url') or str(entry)
                    all_missing[entry_id] = missing
            assert not fail, f'missing values'
            # raise KeyError(all_missing)

        entries = []
        for mod in mods:

            provider = find_matching(mod)
            if provider:
                entry = provider.convert(mod)
                entries.append(dict(entry))
        try:
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.apply_defaults(entry)

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.prepare_dependencies(entry)

            remove = []
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                if not provider.validate(entry):
                    remove.append(entry)
            if remove or self.debug:
                remove_dump = '\n    ' + \
                    yaml.dump(remove).replace('\n', '\n    ')
                print(f'remove: {remove_dump}')
            for rem in remove:
                entries.remove(rem)

            # print(f'entries: \n{yaml.dump(entries)}')

            features = []
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.resolve_dependencies(entry, entries)
            

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.resolve_feature_dependencies(entry, entries, features)

            print(f'features: \n{yaml.dump(features)}')

            if self.debug:
                print(f'resolve dep entries: \n{yaml.dump(entries)}')

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.fill_information(entry)

            assert_dict('fill_information', ('name', 'package_type'), entries)

            # print(f'fill info entries: \n{yaml.dump(entries)}')
            generate_graph(entries, path=data_path, pack_name=pack_name)

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.prepare_download(
                    entry, Path(self.cache_dir, provider._typ))

            assert_dict('prepare_download',
                        ('url', 'file_name', 'cache_path'), [e for e in entries if e['type'] != 'local'])
            assert_dict('prepare_download',
                        ('file_name', 'file'), [e for e in entries if e['type'] == 'local'])

            src_path = Path(output_path, 'src')

            forge_entry = self.get_forge(forge_version, mc_version)
            rmtree(
                str(Path(output_path, forge_entry['path']).resolve()), ignore_errors=True)
            entries.append(forge_entry)

            # resolve full path
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.resolve_path(entry)

            assert_dict('resolve_path', ('path', 'file_path'), entries)

            if self.debug:
                print(f'resolve path entries: \n{yaml.dump(entries)}')

            # TODO: github, jenkins

            # clear old mods
            mod_path = Path(src_path, 'mods')
            rmtree(str(mod_path.resolve()), ignore_errors=True)
            mod_path.mkdir(parents=True, exist_ok=True)

            # for entry in entries:
            #     provider: BaseProvider = provider_map[entry['type']]
            #     provider.write_feature(entry, src_path)

            if urls:
                # requires path to be known
                for entry in entries:
                    provider: BaseProvider = provider_map[entry['type']]
                    provider.write_direct_url(entry, src_path)

            if self.debug:
                print(
                    f'write urls and features entries: \n{yaml.dump(entries)}')

            print('starting download')

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.download(entry, src_path)

        # TODO: generate modpack.json

            # collect features

            features_list = []
            for f in features:
                prop = {
                    'name': f['name'],
                    'description': '',
                    'recommendation': None,
                    'selected': None
                }
                includes = []
                excludes = []
                for entry_ref in f['entry_refs']:
                    entry = next(e for e in entries if e['name'] == entry_ref)
                    include = entry.get('include', [])
                    include.insert(0, entry['target_path'])
                    includes.extend(include)
                    exclude = entry.get('exclude', [])
                    excludes.extend(exclude)
                    description = entry.get('description')
                    if description:
                        prop['description'] += entry_ref + ': ' + description + '\n\n'
                    if not prop['recommendation']: 
                        #TODO: check for last dep level
                        prop['recommendation'] = entry.get('recommendation')
                    if prop.get('selected') == None:
                        #TODO: check for last dep level
                        prop['selected'] = entry.get('selected')
                        
                prop['selected'] = prop.get('selected', False)
                feature = {
                    'properties': prop,
                    'files': {
                        'include': includes,
                        'exclude': excludes
                    }
                }
                features_list.append(feature)

            # generate modpack obj
            modpack = {
                'name': pack_name,
                'title': None,
                'gameVersion': str(mc_version[0]),
                'features': features_list,
                'userFiles': {
                    'include': ['options.txt', 'optionsshaders.txt'],
                    'exclude': []
                },
                'launch': {
                    'flags': [
                        '-Dfml.ignoreInvalidMinecraftCertificates=true'
                    ]
                }
            }

            # TODO: generate features

            # write to json
            modpack_path = Path(output_path, 'modpack.json').resolve()
            print(f'wwriting modpack to {modpack_path}')
            with open(modpack_path, 'w') as modpack_file:
                json.dump(modpack, modpack_file, indent=4 * ' ')

            self.add_to_workspace(location=pack_base)

        except KeyError as ke:
            tb = traceback.format_exc()
            arg = ke.args[0]
            if isinstance(arg, dict):
                arg = dict(arg)
                for entry_id, missing_keys in arg.items():
                    print(
                        f"{entry_id} \n\tis missing \n\t{', '.join(missing_keys)}")
            else:
                print(repr(ke))
                print(f'KeyError {ke} in')
                print(entry)
                print(tb)
            raise ke

    def add_to_workspace(self, location: str):
        path = Path(self.global_config['output'],
                    '.modpacks', 'workspace.json')
        Path(path.parent).mkdir(parents=True, exist_ok=True)
        with open(path, 'r') as workspace_file:
            workspace = json.load(workspace_file)
            locations = [p for p in workspace['packs']
                         if p['location'] == location]
        if locations:
            return
        workspace['packs'].append({'location': location})
        with open(path, 'w') as workspace_file:
            json.dumps(workspace, workspace_file, indent=4 * ' ')

    def get_forge_data(self) -> List[Dict[str, Any]]:
        if self.debug:
            print(
                f'get http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
        r = requests.get(
            f'http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
        r.raise_for_status()
        global addonData
        if r.status_code == 200:
            forge_data = r.json()
            return forge_data
        return None

    def get_forge_url(self, version, mc_version: List[str]) -> (str, str, int):
        if not self.forge_data:
            self.forge_data = self.get_forge_data()
        data = self.forge_data
        if isinstance(mc_version, list):
            mc_version = mc_version[0]
        if isinstance(version, str):
            version_str = version
            if version in ('recommended', 'latest'):
                promo_version = f'{mc_version}-{version}'
                version = data['promos'].get(promo_version)
            else:
                version = data['promos'].get(version_str)
                if not version:
                    version = data['branches'].get(version_str)
                if not version:
                    version = data['mcversion'].get(version_str)
                if isinstance(version, list):
                    version_list = [
                        v for v in version if data['number'][str(v)]['mcversion'] == mc_version]
                    if not version_list:
                        print(f'ERROR: forge searchterm is invalid',
                              file=sys.stderr)
                        exit(-1)
                    version = max(version_list)

        webpath = data['webpath']
        if isinstance(version, int):
            file_data = data['number'][str(version)]
            mcversion = file_data['mcversion']
            forge_version = file_data['version']
            branch = file_data['branch']
            longversion = f'{mcversion}-{forge_version}'
            if branch:
                longversion = f'{longversion}-{branch}'
            filename = f'forge-{longversion}-installer.jar'
            url = f'{webpath}/{longversion}/{filename}'
            return url, filename, longversion
        assert isinstance(
            version, int), 'version should be resolved to buildnumber'

    def get_forge(self, version, mcversion: List[str]):
        url, file_name, longversion = self.get_forge_url(version, mcversion)
        cache_dir = Path(Path(self.cache_dir, 'forge'), str(longversion))

        entry = {'type': 'direct', 'cache_path': str(cache_dir), 'url': url, 'file_name': file_name,
                 'path': '../loaders', 'name': 'Minecraft Forge'}
        return entry
