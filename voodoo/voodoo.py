#!/bin/python3
# -*- coding: utf-8 -*-
import argparse
import io
import sys
import traceback
import warnings
from itertools import groupby
from pathlib import Path
from shutil import rmtree
from typing import Any, Dict, List, Tuple

import appdirs
import pkg_resources
import requests
import ruamel.yaml as yaml
import simplejson as json
from ruamel.yaml.error import ReusedAnchorWarning

from .cftypes import DependencyType, RLType
from .dependency_graph import generate_graph
from .provider import *

warnings.simplefilter("ignore", ReusedAnchorWarning)


def main():  # TODO: move to __main__ ?
    parser = argparse.ArgumentParser(
        description='Download mods from curseforge and other sources')
    parser.add_argument('pack', help='pack definition file')
    parser.add_argument(
        '-c', '--config', default='config/config.yaml', help='config file')
    # parser.add_argument('--auth', help='auth file for github login')
    # parser.add_argument('--username_github', help='github login')
    # parser.add_argument('--password_github', help='github password')
    parser.add_argument('--debug', dest='debug',
                        action='store_true', help='display debug info')
    parser.add_argument('--export', dest='export',
                        action='store_true', help='export into new format, look in data directory for exported pack')
    args, unknown = parser.parse_known_args()
    args = vars(args)

    voodoo = Voodoo(**args)
    voodoo.process_pack()


class Voodoo:
    forge_data = None
    sponge_entry = None

    def __init__(self, config, debug, pack, export):
        self.debug = debug
        self.export = export
        if self.debug:
            print('using encoding {}'.format(sys.stdout.encoding))
        self.config_path = Path(config).resolve()
        self.pack = pack

        self.cache_dir = appdirs.AppDirs(
            appname='voodoo', appauthor='nikky').user_cache_dir

        # parse config
        config_dir = self.config_path.parent
        self.global_config = {}

        config_suffix = self.config_path.suffix
        if config_suffix == '.yaml':
            config_dir.mkdir(parents=True, exist_ok=True)
            output = io.StringIO()

            default_config = pkg_resources.resource_string(__name__, 'data/default.yaml').decode()
            output.write(default_config)
            
            output.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            if self.config_path.exists():
                with open(self.config_path, 'w') as outfile:
                    outfile.write(default_config)
                with open(self.config_path) as infile:
                    output.write(infile.read())

            self.config_str = output.getvalue()
            output.close()

            self.global_config = yaml.safe_load(self.config_str)
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

    def process_pack(self):
        pack_base = self.pack
        print(f'processing {pack_base}')

        pack_config_path = Path(self.pack)

        if not pack_config_path.is_file():
            print(f"no such file: {pack_config_path}")
            pack_config_path = Path(f"{self.pack}.yaml")

        if not pack_config_path.is_absolute():
            if not pack_config_path.is_file():
                print(f"no such file: {pack_config_path}")
                pack_config_base = Path(self.config_path, self.global_config.get('packs'))
                pack_config_path = pack_config_base / self.pack

            if not pack_config_path.is_file():
                print(f"no such file: {pack_config_path}")
                pack_config_base = Path(self.config_path, self.global_config.get('packs'))
                pack_config_path = pack_config_base / f"{self.pack}.yaml"

        if not pack_config_path.is_file():
            print(f"no such file: {pack_config_path}")
            exit(-1)
        else:
            print(f"found: {pack_config_path}")

        if self.export:
            self.exPort(pack_config_path, pack_base)

        output = io.StringIO()
        output.write(self.config_str)
        output.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
        with open(pack_config_path) as infile:
            output.write(infile.read())
        config_str = output.getvalue()
        output.close()
        try:
            pack_config = yaml.safe_load(config_str)
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

        temp_path = pack_config.get('temp_path')
        if temp_path:
            temp_path = Path(self.config_path, temp_path)
            temp_path.mkdir(parents=True, exist_ok=True)
            merged_config_path = temp_path / f'{pack_base}.yaml'
            with open(merged_config_path, 'w') as outfile:
                outfile.write(config_str)

        output_path = Path(pack_config.get('output') or 'modpacks', pack_config.get('name'))
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
        sponge_version = pack_config.get('sponge')
        assert forge_version or sponge_version, 'no Forge or Sponge version defined'

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
            assert not fail, f'{check_name} missing values {all_missing}'
            # raise KeyError(all_missing)
        
        entries = []
        for mod in mods:

            provider = find_matching(mod)
            if provider:
                entry = provider.convert(mod)
                entries.append(dict(entry))


        if sponge_version:
            entries.append(self.get_sponge(sponge_version))
        try:
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.apply_defaults(entry)

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.prepare_dependencies(entry)

            # add forge
            forge_entry = self.get_forge(forge_version, mc_version)
            print(Path(output_path, forge_entry['path']).resolve())
            rmtree(
                str(Path(output_path, forge_entry['path']).resolve()), ignore_errors=True)
            entries.append(forge_entry)

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

            if self.debug:
                print(f'entries: \n{yaml.dump(entries)}')

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

            if self.debug:
                print(f'fill info entries: \n{yaml.dump(entries)}')

            if self.debug:
                print("generating graph")
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

            # resolve full path
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.resolve_path(entry)

            assert_dict('resolve_path', ('path', 'file_path'), entries)

            if self.debug:
                print(f'resolve path entries: \n{yaml.dump(entries)}')

            # TODO: github, jenkins

            # clear old mods
            mod_path = Path(output_path, 'src', 'mods')
            rmtree(str(mod_path.resolve()), ignore_errors=True)
            mod_path.mkdir(parents=True, exist_ok=True)

            # for entry in entries:
            #     provider: BaseProvider = provider_map[entry['type']]
            #     provider.write_feature(entry, src_path)

            if urls:
                # requires path to be known
                for entry in entries:
                    provider: BaseProvider = provider_map[entry['type']]
                    provider.write_direct_url(entry, output_path)

            if self.debug:
                print(
                    f'write urls and features entries: \n{yaml.dump(entries)}')

            print('starting download')

            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.download(entry, output_path)

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
                        prop['description'] += entry_ref + \
                            ': ' + description + '\n\n'
                    if not prop['recommendation']:
                        # TODO: check for last dep level
                        prop['recommendation'] = entry.get('recommendation')
                    if prop.get('selected') == None:
                        # TODO: check for last dep level
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
                'title': pack_config['title'],
                'gameVersion': str(mc_version[0]),
                'features': features_list,
                'userFiles': {
                    'include': pack_config.get('userFiles_include') or ['options.txt', 'optionsshaders.txt'],
                    'exclude': pack_config.get('userFiles_exclude') or []
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
            print(f'writing modpack json to {modpack_path}')
            with open(modpack_path, 'w') as modpack_file:
                json.dump(modpack, modpack_file, indent=4 * ' ')

            self.add_to_workspace(location=pack_base, modpacks_path=pack_config.get('output') or 'modpacks')


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

    def add_to_workspace(self, location: str, modpacks_path: Path):
        location = Path(location).stem
        path = Path(modpacks_path,
                    '.modpacks', 'workspace.json')
        Path(path.parent).mkdir(parents=True, exist_ok=True)

        workspace_default = {
            'packs': [], 'packageListingEntries': [], 'packageListingType': 'STATIC'}
        if not path.exists():
            workspace = workspace_default
        else:
            try:
                with open(path, 'r') as workspace_file:
                    workspace = json.load(workspace_file)
                    locations = [p for p in workspace['packs']
                                 if p['location'] == location]
            except json.JSONDecodeError:
                workspace = workspace_default

        locations = [p for p in workspace['packs']
                     if p['location'] == location]
        if locations:
            print(f'{location} is already in workspace.json')
            return
        workspace['packs'].append({'location': location})
        print(f'writing workspace json to {path}')
        with open(path, 'w') as workspace_file:
            json.dump(workspace, workspace_file, indent=4 * ' ')

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
        if self.sponge_entry:
            sponge_version = self.sponge_entry['version']
            print(sponge_version)
            version = int(sponge_version.split('-')[1])
        url, file_name, longversion = self.get_forge_url(version, mcversion)
        cache_dir = Path(Path(self.cache_dir, 'forge'), str(longversion))

        entry = dict(
            type='direct',
            name='Minecraft Forge',
            cache_path=str(cache_dir),
            url=url,
            file_name=file_name,
            package_type='loader',
            path='loaders',
        )
        return entry

    def get_sponge(self, sponge_version):
        entry = dict(
            type='mvn',
            name='Sponge Forge',
            remote_repository="https://repo.spongepowered.org/maven/",
            group='org.spongepowered',
            artifact='spongeforge',
            version=sponge_version,
            package_type='mod',
            path='mods',
            side='server',
        )
        self.sponge_entry = entry
        return entry


    def exPort(self, pack_config_path, pack_base): #mods: List[Any], mc_version, pack_base, pack_name, data_path):
        output = io.StringIO()

        default_config = pkg_resources.resource_string(__name__, 'data/default_export.yaml').decode()
        output.write(default_config)
        
        output.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
        print(type(pack_config_path))
        print(pack_config_path)
        if pack_config_path.exists():
            with open(pack_config_path) as infile:
                output.write(infile.read())

        config_str = output.getvalue()
        output.close()

        pack_config = yaml.round_trip_load(config_str)
        

        from collections import OrderedDict
        from ruamel.yaml.comments import CommentedMap
        print(pack_config)
        mods = pack_config.get("mods")
        mc_version= pack_config.get('mc_version')

        output_path = Path(pack_config.get('output') or 'modpacks', pack_config.get('name'))
        data_path = Path(pack_config.get('data_path', 'data'))
        assert not data_path.is_absolute(), 'data_path has to be relative to the output path'
        data_path = Path(output_path, data_path)
        data_path.mkdir(parents=True, exist_ok=True)

        # export new config
        def rename(mod: CommentedMap, old, new):
            if old in mod:
                print(type(mod))
                # mod[new] = mod[old]
                # del mod[old]
                # Replace the key and value for key == 0:
                mod = CommentedMap((new, value) if key == old else (key, value) for key, value in mod.items())
                return mod
            # else:
            #     print(f"no key {old}")
            return mod

        for mod in mods:
            print(mod)
            if(isinstance(mod, str)):
                continue
            # if "side" in mod:
            #     # mod["side"] = mod["side"].upper()
            #     del mod["side"]
            if 'type' in mod:
                mod['provider'] = mod["type"].upper()
                del mod["type"]
            if 'path' in mod:
                del mod["path"]
            if "selected" in mod:
                mod["feature"] = dict(selected=True)
                del mod["selected"]
            
            rename(mod, "file_name_regex", "jenkinsFileNameRegex")
            rename(mod, "depends", "dependencies")
            rename(mod, "package_type", "packageType")
            rename(mod, "jenkins_url", "jenkinsUrl")
            rename(mod, "release_type", "releaseTypes")
            rename(mod, "file", "fileSrc")
        pack_config.insert(3, ('validMcVersions'), mc_version[1:])
        pack_config.insert(3, ('mcVersion'), mc_version[0])
        del pack_config['mc_version']
        rename(pack_config, 'optionals', 'doOptionals')
        if 'urls' in pack_config:
            del pack_config['urls']
        if 'release_type' in pack_config:
            del pack_config['release_type']
        
        if 'optionals' in pack_config:
            pack_config['doOptionals'] = pack_config['optionals']
            del pack_config['optionals']

        pack_config['entries'] = pack_config['mods']
        del pack_config['mods']

        with open(data_path / f"{pack_base}.yaml", 'w') as outfile:
            outfile.write(yaml.round_trip_dump(pack_config, default_flow_style=False, indent=2))
        exit()