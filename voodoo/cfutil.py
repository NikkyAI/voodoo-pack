#!/bin/python3
import argparse
import bz2
import os
import shutil
from collections import OrderedDict
from pathlib import Path
from typing import Mapping, Dict, List, Any, Tuple
from urllib.parse import urlparse, unquote, quote, urljoin, urlunsplit

import appdirs
import bs4 as BeautifulSoup
import requests
import rfc6266
import sys
import yaml
import json
from pyhocon import ConfigFactory
from pyhocon import ConfigTree
from pyhocon import HOCONConverter
from requests.auth import HTTPBasicAuth

from .cftypes import RLType, DependencyType
from .loader import Loader

from mavenpy.run import Maven

print('using encoding {}'.format(sys.stdout.encoding))

complete_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2"
complete_timestamp_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2.txt"

parser = argparse.ArgumentParser(
    description="Download mods from curseforge and other sources")
parser.add_argument("--auth", help="auth file for curse login")
parser.add_argument("--config", help="path to config file")
parser.add_argument("--username_github", help="github login")
parser.add_argument("--password_github", help="github password")
parser.add_argument("--debug", dest="debug",
                    action="store_true", help="display debug info")
args, unknown = parser.parse_known_args()

configPath = Path("config.yaml")
if not configPath.exists():
    configPath = Path("config/config.yaml")


def convert_to_dict(conf):
    if isinstance(conf, OrderedDict):
        conf = dict(conf)
        for k, v in conf.items():
            conf[k] = convert_to_dict(v)
    if isinstance(conf, list):
        conf = [convert_to_dict(l) for l in conf]
    return conf


if args.config:
    configPath = Path(args.config)
# config = yaml.load(configPath.open().read())

# find config file# TODO: allow specifiyng directory
configDir = configPath.resolve().parent

config = {}
config_suffix = configPath.suffix
if config_suffix == '.yaml':
    defaultConfigPath = configDir / "config_default.yaml"
    generatedConfigPath = configDir / 'build' / 'generated_config.yaml'
    generatedConfigPath.parent.mkdir(parents=True, exist_ok=True)
    # config = yaml.load(configPath.open().read())
    with open(generatedConfigPath, 'w') as outfile:
        with open(defaultConfigPath) as infile:
            outfile.write(infile.read())
        outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
        with open(configPath) as infile:
            outfile.write(infile.read())

    with open(generatedConfigPath, 'r') as f:
        config = yaml.load(f, Loader)
    print(yaml.dump(config))

# elif config_suffix == '.conf':
#     print(str(configPath))
#     config = convert_to_dict(ConfigFactory.parse_file(
#         str(configPath)).as_plain_ordered_dict())
# if args.debug:
#     print(configPath.name)
#     print(HOCONConverter.to_hocon(config))
#     # print(yaml.dump(config))
#     print('\n')

auth_file = args.auth or config.get('authentication', None)

auth = config.get('authentication', {})
if args.username_github and args.password_github:
    auth_github = {'username': args.username, 'password': args.password}
    auth['github'] = auth_github


outputDir = Path(config.get('output', 'modpacks'))
if not outputDir.exists():
    outputDir.mkdir(parents=True)
downloadUrlsConfig = config.get('urls', False)
downloadUrls = False

downloaderDirs = appdirs.AppDirs(appname="voodoo", appauthor="nikky")
cache_path_curse = Path(downloaderDirs.user_cache_dir, "curse")
cache_path_github = Path(downloaderDirs.user_cache_dir, "github")
cache_path_jenkins = Path(downloaderDirs.user_cache_dir, "jenkins")
cache_path_maven = Path(downloaderDirs.user_cache_dir, "maven")
cache_path_general = Path(downloaderDirs.user_cache_dir)
if not cache_path_curse.exists():
    cache_path_curse.mkdir(parents=True)
if not cache_path_github.exists():
    cache_path_github.mkdir(parents=True)
if not cache_path_jenkins.exists():
    cache_path_jenkins.mkdir(parents=True)
if not cache_path_general.exists():
    cache_path_general.mkdir(parents=True)
print('cache_path: {}'.format(cache_path_curse))


addonData = None

side_map = {
    'client': '_CLIENT',
    'server': '_SERVER'
}


def get_forge_data() -> List[Mapping[str, Any]]:
    if args.debug:
        print(f'get http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
    r = requests.get(
        f'http://files.minecraftforge.net/maven/net/minecraftforge/forge/json')
    r.raise_for_status()
    global addonData
    if r.status_code == 200:
        forge_data = r.json()
        return forge_data
    return None

def get_forge_url(version, mc_version: str) -> (str, str, int) :
    data = get_forge_data()
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

def get_forge(version, mcversion: str, path: Path, cache_base: Path):
    download_url, file_name_on_disk, longversion = get_forge_url(version, mcversion)
    cache_dir = Path(cache_base, str(longversion))

    entry = {'type': 'direct', 'cache_path': str(cache_dir), 'download_url': download_url, 'file_name_on_disk': file_name_on_disk,
    'path': str(path), 'name': f"forge-{longversion}-installer"}
    return entry

