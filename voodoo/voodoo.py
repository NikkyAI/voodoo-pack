#!/bin/python3
# -*- coding: utf-8 -*-
import argparse
import codecs
import yaml
import sys
import appdirs
import requests
from pathlib import Path
from shutil import rmtree
from typing import Any, List, Mapping, Sequence

from .provider import *
from .cftypes import RLType, DependencyType
from .loader import Loader
from .dependency_graph import generate_graph

def run():
    print('using encoding {}'.format(sys.stdout.encoding))

    parser = argparse.ArgumentParser(description="Download mods from curseforge and other sources")
    parser.add_argument("--auth", help="auth file for curse login")
    parser.add_argument("--config", help="path to config file")
    parser.add_argument("--username_github", help="github login")
    parser.add_argument("--password_github", help="github password")
    parser.add_argument("--debug", dest="debug",
                        action="store_true", help="display debug info")
    args, unknown = parser.parse_known_args()

    config_path = Path("config/config.yaml")

    if args.config:
        config_path = Path(args.config)

    config_dir = config_path.resolve().parent

    config = {}
    config_suffix = config_path.suffix
    if config_suffix == '.yaml':
        default_config_path = config_dir / "config_default.yaml"
        generated_config_path = config_dir / 'build' / 'generated_config.yaml'
        generated_config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(generated_config_path, 'w') as outfile:
            with open(default_config_path) as infile:
                outfile.write(infile.read())
            outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(config_path) as infile:
                outfile.write(infile.read())

        with open(generated_config_path, 'r') as f:
            config = yaml.load(f, Loader)
        print(yaml.dump(config))

    auth_file = args.auth or config.get('authentication', None)

    auth = config.get('authentication', {})
    if args.username_github and args.password_github:
        auth_github = {'username': args.username, 'password': args.password}
        auth['github'] = auth_github


    output_dir = Path(config.get('output', 'modpacks'))
    output_dir.mkdir(parents=True, exist_ok=True)
    urls = config.get('urls', True)

    # TODO: move into CurseProvider .ctor
    # addonData = get_addon_data()
    # print("data len: {}".format(len(addonData) / (1024.0 * 1024.0)))
    # modnames = [p['name'] for p in addonData]  # if p["PackageType"] == 6]
    # with codecs.open('./modlist.txt', "w", encoding='utf8') as modlist:
    #     modlist.write("\n".join(modnames))




    print(f"config: {config}")
    for pack, pack_meta_config in config["modpacks"].items():
        print(f"name: '{pack}'")
        if not pack_meta_config['enabled']:
            print("skipped")
            continue
        print(yaml.dump(pack_meta_config))
        pack_base = pack  # TODO: file base
        pack_configpath = config_dir / 'packs' / f"{pack_base}.yaml"
        defaultpack_configPath = config_dir / "pack_default.yaml"
        generatedpack_configPath = config_dir / "build" / \
            f"{pack_base}.yaml"  # TODO: make sure directory exists
        generatedpack_configPath.parent.mkdir(parents=True, exist_ok=True)
        # config = yaml.load(configPath.open().read())
        with open(generatedpack_configPath, 'w') as outfile:
            with open(generated_config_path) as infile:
                outfile.write(infile.read())
            outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(defaultpack_configPath) as infile:
                outfile.write(infile.read())
            outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(pack_configpath) as infile:
                outfile.write(infile.read())

        with open(generatedpack_configPath, 'r') as f:
            pack_config = yaml.load(f, Loader)

        output_base = Path(pack_config.get('output') or 'modpacks', pack).resolve()
        print(yaml.dump(pack_config))

        pack_name = pack_config.get('name' or pack)
        download_optional = pack_config.get("optionals", False)
        game_version = pack_config.get("mc_version", "1.10.2")
        forge_version = pack_config.get("forge", "recommended")
        default_release_types = pack_config.get('release_type', (RLType.Release, RLType.Beta, RLType.Alpha))

        providers: List[BaseProvider] = []
        providers.append(DirectProvider())
        providers.append(LocalProvider(Path(output_base, 'local')))
        curse_args = (args.debug, download_optional,
                      game_version, default_release_types)
        providers.append(CurseProvider(*curse_args))
        providers.append(MavenProvider())
        providers.append(GithubProvider())

        # TODO: provider.apply_config()


        print('output base {}'.format(output_base))
        mods = pack_config.get("mods", [])

        provider_map = {p.typ: p for p in providers}

        def find_matching(mod: Any) -> BaseProvider:
            for provider in providers:
                for provider in providers:
                    if provider.match(mod):
                        return provider
            return None

        entries = []
        for mod in mods:

            provider = find_matching(mod)
            if provider:
                entry = provider.convert(mod)
                entries.append(dict(entry))

        remove = []
        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            if not provider.prepare_dependencies(entry): #TODO: ranme to filter - something
                remove.append(entry)
        remove_dump = yaml.dump(remove).replace('\n', '\n    ')
        print(f"remove: \n    {remove_dump}")
        for rem in remove:
            entries.remove(rem)

        # print(f"entries: \n{yaml.dump(entries)}")

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.resolve_dependencies(entry, entries)

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.resolve_feature_dependencies(entry, entries)

        # if args.debug:
            # print(f"resolve dep entries: \n{yaml.dump(entries)}")

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.fill_information(entry)

        # print(f"fill info entries: \n{yaml.dump(entries)}")
        generate_graph(entries, output_base)

        cache_dir = appdirs.AppDirs(appname="voodoo", appauthor="nikky").user_cache_dir

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.prepare_download(entry, Path(cache_dir, provider.typ))

        src_path = Path(output_base, 'src')
        
        loader_path = Path(output_base, 'loaders')
        rmtree(str(loader_path.resolve()), ignore_errors=True)
        loader_path.mkdir(parents=True, exist_ok=True)
        forge_entry = get_forge(forge_version, game_version, loader_path, Path(cache_dir, 'forge'), args.debug)
        entries.append(forge_entry)
        
        # resolve full path
        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.resolve_path(entry)

        if args.debug:
            print(f"resolve path entries: \n{yaml.dump(entries)}")

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.write_feature(entry, src_path)
        
        if args.debug:
            print(f"write urls and features entries: \n{yaml.dump(entries)}")


        if urls:
            # requires path to be known
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.write_direct_url(entry, src_path)

        # TODO: github, jenkins, local

        # clear old mods
        mod_path = Path(src_path, 'mods')
        rmtree(str(mod_path.resolve()), ignore_errors=True)
        mod_path.mkdir(parents=True, exist_ok=True)

        print('starting download')

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.download(entry, src_path)

        exit(0)

def get_forge_data(debug: bool = False) -> List[Mapping[str, Any]]:
    if debug:
        print(f'get http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
    r = requests.get(
        f'http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
    r.raise_for_status()
    global addonData
    if r.status_code == 200:
        forge_data = r.json()
        return forge_data
    return None

def get_forge_url(version, mc_version: str, debug: bool = False) -> (str, str, int) :
    data = get_forge_data(debug)
    if isinstance(version, str):
        version_str = version
        if version in ('recommended', 'latest'):
            promo_version = f"{mc_version}-{version}"
            version = data['promos'].get(promo_version)
        else:
            version = data['promos'].get(version_str)
            if not version:
                version = data['branches'].get(version_str)
            if not version:
                version = data['mcversion'].get(version_str)
            if isinstance(version, list):
                # TODO: filter list based on mc_version
                version_list = [v for v in version if data['number'][str(v)]['mcversion'] == mc_version]
                if(len(version_list) == 0):
                    print(f"ERROR: forge searchterm is invalid", file=sys.stderr)
                    exit(-1)
                version = max(version_list)

    webpath = data['webpath']
    if isinstance(version, int):
        file_data = data['number'][str(version)]
        mcversion = file_data['mcversion']
        forge_version = file_data['version']
        branch = file_data['branch']
        longversion = f"{mcversion}-{forge_version}"
        if branch:
            longversion = f"{longversion}-{branch}"
        filename = f"forge-{longversion}-installer.jar"
        url = f"{webpath}/{longversion}/{filename}"
        return url, filename, longversion

def get_forge(version, mcversion: str, path: Path, cache_base: Path, debug: bool = False):
    download_url, file_name_on_disk, longversion = get_forge_url(version, mcversion, debug)
    cache_dir = Path(cache_base, str(longversion))

    entry = {'type': 'direct', 'cache_path': str(cache_dir), 'download_url': download_url, 'file_name_on_disk': file_name_on_disk,
    'path': str(path), 'name': "Minecraft Forge"}
    return entry
