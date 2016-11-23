#!/bin/python3
import argparse
from typing import Mapping, Dict, List, Any, Tuple
from urllib.parse import urlparse, unquote
import appdirs
import json
from pathlib import Path
import requests
import shutil
import bz2
import rfc6266
import yaml
from lxml import html

from .types import RLType, DependencyType

complete_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2"
complete_timestamp_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2.txt"

parser = argparse.ArgumentParser(description="Download Curse modpack mods")
parser.add_argument("--auth", help="auth file for curse login")
parser.add_argument("--config", help="path to config file")
parser.add_argument("--username", help="curse login")
parser.add_argument("--password", help="curse password")
args, unknown = parser.parse_known_args()


configPath = Path("config/config.yaml")
if args.config:
    configPath = Path(args.config)
# config = yaml.load(configPath.open().read())
config = {}
config_suffix = configPath.suffix
if config_suffix == '.json':
    config = json.loads(configPath.open().read())
elif config_suffix == '.yaml':
    config = yaml.load(configPath.open().read())
print(yaml.dump(config))

auth_file = args.auth or config.get('authentication', None)

auth = None
if args.username and args.password:
    auth = {'username': args.username, 'password': args.password}


outputDir = Path(config.get('output', 'modpacks'))
if not outputDir.exists():
    outputDir.mkdir(parents=True, exist_ok=True)
downloadUrls = config.get('urls', False)

downloaderDirs = appdirs.AppDirs(appname="cursePacker", appauthor="nikky")
cache_path = Path(downloaderDirs.user_cache_dir, "packCache")
if not cache_path.exists():
    cache_path.mkdir(parents=True)
print('cache_path: {}'.format(cache_path))


ProjectData = None

side_map = {
    'client': '_CLIENT',
    'server': '_SERVER'
}

def get_project_data() -> List[Mapping[str, Any]]:
    
    timestamp_path = Path(cache_path / "timestamp.txt")
    json_path = Path(cache_path / "complete.json")
    no_download = False
    if timestamp_path.is_file():
        print('downloading timestamp')
        timestamp_response = requests.get(
            complete_timestamp_url)
        timestamp = timestamp_response.content.decode("utf-8")
        old_timestamp = timestamp_path.open().read()

        if old_timestamp == timestamp and json_path.is_file():
            no_download = True
    # no_download = False
    if not no_download:
        print("downloading complete.json.bz2")

        json_response = requests.get(complete_url)
        print("decompressing response")
        json_bytes = bz2.decompress(json_response.content)
        print("writing json")
        json_path.write_bytes(json_bytes)
        print("decoding json")
        json_data = json_bytes.decode('utf-8')
    else:
        # load file from cache
        print("reading json from cache")
        json_data = json_path.open('r', encoding='utf-8').read()
    
    complete = json.loads(json_data)
    global ProjectData
    ProjectData = complete["data"]
    # save new timestamp
    timestamp_path.write_text(str(complete["timestamp"]))
    return ProjectData


defaultGameVersion = "1.10.2"
default_release_types = (RLType.Release, RLType.Beta, RLType.Alpha)


def find_curse_file(mc_version: str=defaultGameVersion,
                    name: str = None,
                    version: str= None,
                    release_type: List[Any]=default_release_types,
                    project_id: int=None
                    )-> Tuple[int, int, str]:
    release_type = list(release_type)
    release_type = [RLType.get(t) for t in release_type]
    project = {}

    global ProjectData
    if not ProjectData:
        ProjectData = get_project_data()

    found = False
    for project in ProjectData:
        category_section = project.get("CategorySection", None)
        if not category_section:
            print("entry does not have a categories section")
            continue

        if not category_section["GameID"] == 432:
            continue

        if not project['PackageType'] == 6:
            continue

        # project related filters
        if (name and name == project['Name']) or (project_id and project_id == project['Id']):
            found = True
            break

    # process project
    if not found:
        print(name + ' not found')
        return -1, -1, ''

    project_id = project["Id"]

    if not version:
        # filter by game version and release type
        latest_files = [f for f in project["LatestFiles"]
                        if mc_version in f['GameVersion']
                        and RLType.get(f['ReleaseType'])
                        in release_type]
        if latest_files:
            # sort by date
            latest_files.sort(key=lambda x: (x['FileDate']))
            # sort by release type so that alpha, beta, release ordering is achieved
            latest_files.sort(key=lambda x: (x['ReleaseType']), reverse=True)
            file = latest_files[0]
            return project_id, file["Id"], file['FileName']

        else:
            game_version_latest_files = [f for f in project["GameVersionLatestFiles"]
                                         if mc_version in f['GameVesion']
                                         and RLType.get(f['FileType']) in release_type]
            if game_version_latest_files:
                # sort by version (in name) descending, so highest version first
                game_version_latest_files.sort(key=lambda x: (x['GameVesion']), reverse=True)
                # sort by release type so that alpha, beta, release ordering is achieved
                game_version_latest_files.sort(key=lambda x: (x['FileType']), reverse=True)
                file = game_version_latest_files[0]
                return project_id, file['ProjectFileID'], file['ProjectFileName']

    files = get_add_on_files(project['Id'])
    # TODO improve and add version detection
    # ModVersion in f['file_name']
    files = [f for f in files
             if version and version in f['file_name'] or not version
             and mc_version in f['game_version']
             and RLType.get(f['release_type']) in release_type]
    if files:
        # print('filtered files:')
        # for file in files:
        #    print('{0[release_type]} {0[id]} {0[file_name]}: {0[game_version]}'.format(file))

        # TODO make sure sorting with arrays as values works
        # sort by version (in name) descending, so highest version first
        files.sort(key=lambda x: (x['game_version']), reverse=True)
        # sort by release type so that alpha, beta, release ordering is achieved
        files.sort(key=lambda x: RLType.get(x['release_type']), reverse=True)
        file = files[0]
        # print('sorted files:')
        # for file in files:
        #    print('{0[release_type]} {0[id]} {0[file_name]}: {0[game_version]}'.format(file))
        print('dependencies {}'.format(file['dependencies']))
        return project_id, file['id'], file['file_name']

    print('no matching version found for: {0[Name]} project url: {0[WebSiteURL]}'.format(project))
    return project_id, -1, ''

iLen = 0
i = 0
session = None

def download(minecraft_path: Path,
             download_list: List[Dict[str, Any]]=(),
             curse_optional: bool=False
             ):
    # minecraft_path = Path(minecraft_folder)
    if not minecraft_path.exists():
        print('mkdir {}'.format(minecraft_path))
        minecraft_path.mkdir(parents=True)
    mods_path = minecraft_path / "mods"
    if mods_path.exists():
        print('rm -r {}'.format(mods_path))
        # clean and recreate directory
        shutil.rmtree(str(mods_path))
    print('mkdir {}'.format(mods_path))
    mods_path.mkdir()

    global iLen, i, session
    iLen = len(download_list)
    session = requests.session()

    for download_entry in download_list:
        # print(download)
        download_type = download_entry['type']

        # side
        effective_path = mods_path
        if 'side' in download_entry:
            effective_path /= side_map.get(download_entry['side'], '')

        if not effective_path.exists():
            print('mkdir {}'.format(effective_path))
            effective_path.mkdir(parents=True)

        file = None
        name = None

        if download_type == 'direct':
            direct_parameter = {key: download_entry[key] for key in ["direct"] if key in download_entry}
            file, name = download_direct(mods_path=effective_path, **direct_parameter)

        if download_type == 'curse':
            curse_parameter = {key: download_entry[key] for key in ['project_id', 'file_id', 'optional']
                if key in download_entry}
            optional = download_entry.get('optional', curse_optional)
            # optional = download_entry['optional'] if ('optional' in download_entry and download_entry['optional'] is not None) else curse_optional

            file, name = download_curse(mods_path=effective_path, download_list=download_list, download_optional=optional, **curse_parameter)

        if download_type == 'github':
            continue

        feature = download_entry.get('feature', None)
        if feature is not None:
            if file:
                with open(str(file) + '.info.json', "w") as info_file:
                    if not 'name' in feature and name:
                        feature['name'] = name
                    info_dict = {'feature': feature}
                    json.dump(info_dict, info_file)


def download_curse(mods_path: Path, project_id: int, file_id: int, download_optional: bool = False, download_list: List[Dict[str, Any]]=list(())) -> (Path, str):
    global iLen, i, session

    dep_cache_dir = cache_path / str(project_id) / str(file_id)
    addon = get_add_on(project_id)
    file = get_add_on_file(project_id, file_id)
    for dependency in file['dependencies']:
        dep_type = DependencyType.get(dependency['type'])
        add_on_id = dependency['add_on_id']
        #for download in download_list:
            #print(get_add_on(download['project_id']))
        if add_on_id in [download['project_id'] for download in download_list if download['type'] == 'curse' and 'project_id' in download]:
            # dependency project is already in the download list
            continue

        # opt = if op
        if dep_type == DependencyType.Required or \
                (dep_type == DependencyType.Optional and (download_optional)):
            project_id, file_id, file_name = find_curse_file(project_id=add_on_id)
            if project_id > 0 and file_id > 0:
                download_list.append({'project_id': project_id, 'file_id': file_id, 'type': 'curse'})
                iLen += 1  # hope this is about righttio
                print(
                    'added {} dependency {} \nof {} at {}'.format(dep_type, file_name, addon['name'], iLen))

    file_name_on_disk = file['file_name_on_disk']
    if downloadUrls:
        i += 1
        url_file_name = "{}.url.txt".format(file_name_on_disk)
        print("[{}/{}] {}".format(i, iLen, url_file_name))
        with open(str(mods_path / url_file_name), "wb") as urlFile:
            urlFile.write(str.encode(file['download_url']))

    # look for files in cache
    if dep_cache_dir.is_dir():
        # File is cached
        dep_files = [f for f in dep_cache_dir.iterdir()]
        if len(dep_files) >= 1:
            target_file = mods_path / dep_files[0].name
            i += 1
            print("[{0:d}/{1:d}] {2:s} (cached)".format(i, iLen, target_file.name))
            shutil.copyfile(str(dep_files[0]), str(target_file))

            # TODO add caching
            return target_file, addon['name']

    # File is not cached and needs to be downloaded
    download_url = file['download_url']
    file_response = session.get(download_url, stream=True)
    while file_response.is_redirect:
        source = file_response
        file_response = session.get(source, stream=True)

    # write jarfile
    path = mods_path / file_name_on_disk
    with open(str(path), "wb") as mod:
        mod.write(file_response.content)

    # Try to add file to cache.
    if not dep_cache_dir.exists():
        dep_cache_dir.mkdir(parents=True)
    with open(str(dep_cache_dir / file_name_on_disk), "wb") as mod:
        mod.write(file_response.content)

    return path, addon['name']


def download_direct(mods_path: Path, direct: str) -> (Path, str):
    global iLen, i, session
    url = direct

    disable_url = False
    # File is not cached and needs to be downloaded
    file_response = session.get(url, stream=True)
    while file_response.is_redirect:
        source = file_response
        file_response = session.get(source, stream=True)
    if 'JSESSIONID' in file_response.cookies:
        # special case just for http://optifine.net
        parsed_uri = urlparse(file_response.url)
        tree = html.fromstring(file_response.content)
        resource = tree.xpath('//*[@id="Download"]/a/@href')[0]
        link = '{uri.scheme}://{uri.netloc}/{res}' \
            .format(uri=parsed_uri, res=resource)
        file_response = session.get(link, stream=True)
        disable_url = True
    content_disposition = file_response.headers.get('Content-Disposition', False)
    if content_disposition:
        file_name = rfc6266.parse_headers(content_disposition).filename_unsafe
    else:
        print('cannot find Content-Disposition header, are you sure this download link is valid?')
        # TODO find filename through alternative methods
        return None, ''

    i += 1
    print("[{}/{}] {}".format(i, iLen, file_name))

    path = mods_path / file_name
    with open(str(path), "wb") as mod:
        mod.write(file_response.content)

    if downloadUrls and not disable_url:
        url = unquote(file_response.url)
        url_name = "{}.url.txt".format(file_name)
        print("[{}/{}] {}".format(i, iLen, url_name))
        with open(str(mods_path / url_name), "wb") as urlFile:
            urlFile.write(str.encode(url))

    return path, file_name


authorization = False


def authenticate():
    global auth, auth_file
    if not auth:
        if auth_file:
            auth_path = Path(configPath.parent / auth_file)
            auth_suffix = auth_path.suffix
            if auth_suffix == '.json':
                auth = json.loads(auth_path.open().read())
            elif auth_suffix == '.yaml':
                auth = yaml.load(auth_path.open().read())
        else:
            raise NameError('no_curse_authentication')
    print('post https://curse-rest-proxy.azurewebsites.net/api/authenticate')
    r = requests.post('https://curse-rest-proxy.azurewebsites.net/api/authenticate',
                      json=auth)
    r.raise_for_status()
    if r.status_code == 400:
        message = r.json()["message"]
        raise Exception(message)

    if r.status_code == 200:
        response_data = r.json()
        session = response_data["session"]
        global authorization
        authorization = 'Token {0[user_id]}:{0[token]}'.format(session)


def get_add_on(project_id: int) -> Dict[str, Any]:
    global fileCache
    project_files = fileCache.get(project_id, None)
    if not project_files:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)
    while not authorization:
        authenticate()
    print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}'
          .format(project_id))
    r = requests.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}'
        .format(project_id),
        headers={'Authorization': authorization}
    )
    r.raise_for_status()
    if r.status_code == 200:
        addon = r.json()
        for file in addon['latest_files']:
            project_files[file['id']] = file
        return addon

fileCache = {}


def get_add_on_files(project_id: int) -> List[Dict[str, Any]]:
    global fileCache
    project_files = fileCache.get(project_id, None)
    if not project_files:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)
    while not authorization:
        authenticate()
    print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/files'.format(project_id))
    r = requests.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/files'
        .format(project_id), headers={'Authorization': authorization}
    )
    r.raise_for_status()
    if r.status_code == 200:
        response_data = r.json()
        files = response_data["files"]
        for file in files:
            project_files[file['id']] = file
        return files


def get_add_on_file(project_id: int, file_id: int) -> Dict[str, Any]:
    global fileCache
    project_files = fileCache.get(project_id, None)
    if project_files:
        file = project_files.get(file_id, None)
        if file:
            return file
    else:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)

    while not authorization:
        authenticate()
    print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/file/{1}'.format(project_id, file_id))
    r = requests.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/file/{1}'
        .format(project_id, file_id),
        headers={'Authorization': authorization}
    )
    r.raise_for_status()
    if r.status_code == 200:
        file = r.json()
        project_files[file_id] = file

        return file
