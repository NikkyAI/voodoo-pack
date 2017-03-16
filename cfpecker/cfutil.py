#!/bin/python3
import argparse
import bz2
import json
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
from pyhocon import ConfigFactory
from pyhocon import ConfigTree
from pyhocon import HOCONConverter
from requests.auth import HTTPBasicAuth

from .cftypes import RLType, DependencyType

from mavenpy.run import Maven

complete_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2"
complete_timestamp_url = "http://clientupdate-v6.cursecdn.com/feed/addons/432/v10/complete.json.bz2.txt"

parser = argparse.ArgumentParser(description="Download mods from curseforge and other sources")
parser.add_argument("--auth", help="auth file for curse login")
parser.add_argument("--config", help="path to config file")
parser.add_argument("--username_curse", help="curse login")
parser.add_argument("--password_curse", help="curse password")
parser.add_argument("--username_github", help="github login")
parser.add_argument("--password_github", help="github password")
parser.add_argument("--debug", dest="debug", action="store_true", help="display debug info")
args, unknown = parser.parse_known_args()


configPath = Path("cfpecker.conf")
if not configPath.exists(): configPath = Path("config/cfpecker.conf")

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
config = {}
config_suffix = configPath.suffix
if config_suffix == '.json':
    config = json.loads(configPath.open().read())
elif config_suffix == '.yaml':
    config = yaml.load(configPath.open().read())
elif config_suffix == '.conf':
    print(str(configPath))
    config = convert_to_dict(ConfigFactory.parse_file(str(configPath)).as_plain_ordered_dict())
if args.debug:
    print(configPath.name)
    print(HOCONConverter.to_hocon(config))
    # print(yaml.dump(config))
    print('\n')

auth_file = args.auth or config.get('authentication', None)

auth = config['authentication']
auth_curse = None
if args.username_curse and args.password_curse:
    auth_curse = {'username': args.username, 'password': args.password}
    auth['curse'] = auth_curse
if args.username_github and args.password_github:
    auth_github = {'username': args.username, 'password': args.password}
    auth['github'] = auth_github


outputDir = Path(config.get('output', 'modpacks'))
if not outputDir.exists():
    outputDir.mkdir(parents=True)
downloadUrlsConfig = config.get('urls', False)
downloadUrls = False

downloaderDirs = appdirs.AppDirs(appname="cfpecker", appauthor="nikky")
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


ProjectData = None

side_map = {
    'client': '_CLIENT',
    'server': '_SERVER'
}

def get_project_data() -> List[Mapping[str, Any]]:
    
    timestamp_path = Path(cache_path_general / "complete.json.txt")
    json_path = Path(cache_path_general / "complete.json")
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
        print(name or str(project_id) + ' not found')
        return -1, -1, ''

    project_id = project["Id"]

    if not version:
        # filter by game version and release type

        # latest files lists older beta versions instead of newer releases

        # latest_files = [f for f in project["LatestFiles"]
        #                 if mc_version in f['GameVersion']
        #                 and RLType.get(f['ReleaseType'])
        #                 in release_type]
        # if latest_files:
        #     # sort by release type so that alpha, beta, release ordering is achieved
        #     # latest_files.sort(key=lambda x: (x['ReleaseType']), reverse=True)
        #     # sort by date
        #     latest_files.sort(key=lambda x: (x['FileDate']), reverse=True)
        #     print('latest_files')
        #     for f in project["LatestFiles"]:
        #         print(f['FileName'])
        #     print('filtered')
        #     for f in latest_files:
        #         print(f['FileName'])
        #     file = latest_files[0]
        #     return project_id, file["Id"], file['FileName']
        #
        # else:
            game_version_latest_files = [f for f in project["GameVersionLatestFiles"]
                                         if mc_version == f['GameVesion']
                                         and RLType.get(f['FileType']) in release_type]
            if game_version_latest_files:
                # default sorting is by date
                # print(mc_version)
                # print('game version latest files')
                # for f in project["GameVersionLatestFiles"]:
                #     print(f)
                # print('filtered')
                # for f in game_version_latest_files:
                #     print(f)
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
        # sort by date
        files.sort(key=lambda x: x['file_date'], reverse=True)
        # print('addon_files')
        # for f in files:
        #     print(f)
        file = files[0]
        return project_id, file['id'], file['file_name']

    print('no matching version found for: {0[Name]} project url: {0[WebSiteURL]}'.format(project))
    return project_id, -1, ''

iLen = 0
i = 0
session = None

def download(minecraft_path: Path,
             download_list: List[Dict[str, Any]]=(),
             curse_optional: bool=False,
             direct_urls: bool=True,
             gameVersion: str=defaultGameVersion
             ):
    global downloadUrls
    downloadUrls = direct_urls and downloadUrlsConfig

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
    i = 0
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

        elif download_type == 'curse':
            curse_parameter = download_entry['curse']
            optional = download_entry.get('optional', curse_optional)
            file, name = download_curse(mods_path=effective_path, download_list=download_list, download_optional=optional, mc_version=gameVersion, **curse_parameter)

        elif download_type == 'github':
            github_parameter = download_entry['github']
            file, name = download_github(mods_path=effective_path, **github_parameter)

        elif download_type == 'jenkins':
            jenkins_parameter = download_entry['jenkins']
            file, name = download_jenkins(mods_path=effective_path, **jenkins_parameter)

        elif download_type == 'mvn':
            maven_parameter = download_entry['mvn']
            file, name = download_maven(mods_path=effective_path, **maven_parameter)

        elif download_type == 'local':
            local_parameter = download_entry['local']
            file, name = download_local(mods_path=effective_path, **local_parameter)

        feature = download_entry.get('feature', None)
        if feature is not None:
            if file:
                with open(str(file) + '.info.json', "w") as info_file:
                    if not 'name' in feature and name:
                        feature['name'] = name
                    info_dict = {'feature': feature}
                    json.dump(info_dict, info_file)



session_github = None

def initialize_github():
    global session_github
    session_github = requests.session()
    github_auth = auth.get('github', None)
    if github_auth and 'username' in github_auth and 'password' in github_auth:
        session_github.auth = HTTPBasicAuth(github_auth['username'], github_auth['password'])


def download_github(mods_path: Path, user: str, repo: str=None, tag:str=None) -> (Path, str):
    global iLen, i, session_github
    
    if not session_github:
        initialize_github()
    
    if tag:
        api_url = urljoin('https://api.github.com', 'repos/{user}/{repo}/releases/tags/{tag}'.format(**locals()))
    else:
        api_url = urljoin('https://api.github.com', 'repos/{user}/{repo}/releases'.format(**locals()))

    if args.debug:
        print('GET {}'.format(api_url))
    r = session_github.get(api_url)
    r.raise_for_status()
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            data.sort(key=lambda x: (x['created_at']), reverse=True)
            data = data[0] # TODO pick first or specific tag name
        assets = data['assets']
        file_name = None
        asset_url = None
        tag = data['tag_name']
        dep_cache_dir = cache_path_github / user / repo / tag
        for asset in assets:
            file_name = asset['name']
            asset_url = asset['url']
            if file_name.endswith('sources.jar') or file_name.endswith('api.jar') or file_name.endswith('deobf.jar'):
                continue
            asset_url = asset['url']
            break

        if asset_url:

            if downloadUrls:
                url_file_name = "{}.url.txt".format(file_name)
                print("[{}/{}] {}".format(i, iLen, url_file_name))
                with open(str(mods_path / url_file_name), "wb") as urlFile:
                    urlFile.write(str.encode(asset_url))

            # look for files in cache
            ETag = None
            dep_file = dep_cache_dir / file_name
            etag_file = dep_cache_dir / (file_name + '.etag')
            if dep_file.exists() and etag_file.exists():
                # File might be cached
                etag = etag_file.open().read()

            headers = {}
            if ETag:
                headers['if-none-match'] = ETag
            file_response = session_github.get(asset_url, stream=True, headers=headers)
            file_response.raise_for_status()
            response_etag = file_response.headers['ETag']
            if file_response.status_code == requests.codes.not_modified:
                # Correct file is cached
                target_file = mods_path / dep_file.name

                i += 1
                print("[{}/{}] {} (cached)".format(i, iLen, target_file.name))
                shutil.copyfile(str(dep_file), str(target_file))

                with open(str(dep_cache_dir / (file_name + '.etag')), "wb") as mod:
                    mod.write(str.encode(response_etag))

                return target_file, repo

            i += 1
            print("[{}/{}] {}/{} -> {}".format(i, iLen, user, repo, file_name))

            # write jarfile
            path = mods_path / file_name
            with open(str(path), "wb") as mod:
                mod.write(file_response.content)

            # Try to add file to cache.
            if not dep_cache_dir.exists():
                dep_cache_dir.mkdir(parents=True)
            with open(str(dep_cache_dir / file_name), "wb") as mod:
                mod.write(file_response.content)
            with open(str(dep_cache_dir / (file_name + '.etag')), "wb") as mod:
                mod.write(str.encode(response_etag))

            return path, repo


def download_maven(mods_path: Path, group, artifact, version, classifier=None, packaging=None, remoteRepository="http://repo1.mvn.org/maven2") -> (Path, str):
    global iLen, i, session


    parameters = dict(
                        remoteRepositories=remoteRepository,
                        groupId=group,
                        artifactId=artifact,
                        version=version,
                        dest=str(mods_path)
    )
    if packaging:
        parameters['packaging'] = packaging

    if classifier:
        parameters['classifier'] = classifier

    path = None

    mvn = Maven()
    try:
        mvn.run_in_dir(".", "dependency:get", **parameters)

        file_name = f"{artifact}-{version}.jar"
        path = mods_path / file_name

        url = urljoin(remoteRepository, f"{group.replace('.', '/')}/{artifact}/{version}/{file_name}")

        if downloadUrls:
            url_file_name = "{}.url.txt".format(file_name)
            print("[{}/{}] {}".format(i, iLen, url_file_name))
            with open(str(mods_path / url_file_name), "wb") as urlFile:
                urlFile.write(str.encode(url))

        print("[{}/{}] {}/{}:{} -> {}".format(i, iLen, group, artifact, version, file_name))

    except:
        print("[{}/{}] {}".format(i, iLen, "error executing maven"))

    i += 1

    return path, artifact

def download_local(mods_path: Path, local_file) -> (Path, str):
    global iLen, i

    file_name = os.path.basename(local_file)
    path = mods_path / file_name

    print("[{}/{}] {} -> {}".format(i, iLen, local_file, path))

    shutil.copyfile(local_file, str(path))

    i += 1

    return path, file_name



def download_jenkins(mods_path: Path, url: str, name: str, branch: str='master', build_type: str='lastStableBuild') -> (Path, str):
    global iLen, i, session
    _url = urlparse(url)
    if not _url.scheme:
        url = urlunsplit(('http', _url.path, '', '', ''))
    branch_quote = quote(branch, safe='')
    branch_quote = quote(branch_quote, safe='')
    api_url = urljoin(url, 'job/{name}/branch/{branch_quote}/{build_type}/api/json'.format(**locals()))
    r = session.get(api_url)
    r.raise_for_status()
    if r.status_code == 200:
        data = r.json()
        artifacts = data['artifacts']
        file_name = None
        artifact_url = None
        dep_cache_dir = cache_path_jenkins / name / branch
        for artifact in artifacts:
            file_name = artifact['fileName']
            relative_path = artifact['relativePath']
            if file_name.endswith('sources.jar') or file_name.endswith('api.jar') or file_name.endswith('deobf.jar'):
                continue
            artifact_url = urljoin(url, 'job/{name}/branch/{branch_quote}/{build_type}/artifact/{relative_path}'.format(**locals()))
            break
        if artifact_url:

            if downloadUrls:
                url_file_name = "{}.url.txt".format(file_name)
                print("[{}/{}] {}".format(i, iLen, url_file_name))
                with open(str(mods_path / url_file_name), "wb") as urlFile:
                    urlFile.write(str.encode(artifact_url))

            # look for files in cache
            last_modified = None
            dep_file = dep_cache_dir / file_name
            etag_file = dep_cache_dir / (file_name + '.last-modified')
            if dep_file.exists() and etag_file.exists():
                # File might be cached
                etag = etag_file.open().read()

            print(last_modified)
            # headers = {}
            # if last_modified:
            #     headers['if-modified-since'] = last_modified

            # matching artifact
            file_response = session.get(artifact_url, stream=True, headers={'if-modified-since': last_modified})
            file_response.raise_for_status()

            response_last_modified = file_response.headers.get('Last-Modified', None)
            if file_response.status_code == requests.codes.not_modified:
                # Correct file is cached
                target_file = mods_path / dep_file.name

                i += 1
                print("[{}/{}] {} (cached)".format(i, iLen, target_file.name))
                shutil.copyfile(str(dep_file), str(target_file))

                return target_file, name

            i += 1
            print("[{}/{}] {} -> {}".format(i, iLen, artifact_url, file_name))

            # write jarfile
            path = mods_path / file_name
            with open(str(path), "wb") as mod:
                mod.write(file_response.content)


            if not dep_cache_dir.exists():
                dep_cache_dir.mkdir(parents=True)
            with open(str(dep_cache_dir / file_name), "wb") as mod:
                mod.write(file_response.content)
            if response_last_modified:
                with open(str(dep_cache_dir / (file_name + '.last-modified')), "wb") as mod:
                    mod.write(str.encode(response_last_modified))

            return path, name
    return None, name


def download_curse(mods_path: Path, project_id: int, file_id: int, download_optional: bool = False, download_list: List[Dict[str, Any]]=list(), mc_version: str=defaultGameVersion) -> (Path, str):
    global iLen, i, session

    dep_cache_dir = cache_path_curse / str(project_id) / str(file_id)
    addon = get_add_on(project_id)
    file = get_add_on_file(project_id, file_id)
    for dependency in file['dependencies']:
        dep_type = DependencyType.get(dependency['type'])
        add_on_id = dependency['add_on_id']
        for download in download_list:
            if 'type' not in download:
                print(f"missing type in {download}", file=sys.stderr)
        if add_on_id in [download['curse']['project_id'] for download in download_list if download['type'] == 'curse' and 'curse' in download]:
            # dependency project is already in the download list
            continue

        # opt = if op
        if dep_type == DependencyType.Required or \
                (dep_type == DependencyType.Optional and (download_optional)):
            project_id, file_id, file_name = find_curse_file(project_id=add_on_id, mc_version=mc_version)
            if project_id > 0 and file_id > 0:
                download_list.append({'curse': {'project_id': project_id, 'file_id': file_id}, 'type': 'curse'})
                iLen += 1  # hope this is about right
                print(
                    'added {} dependency {} \nof {} at {} id: {}'.format(dep_type, file_name, addon['name'], iLen, project_id))

    i += 1
    file_name_on_disk = file['file_name_on_disk']
    if downloadUrls:
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
            # i += 1
            print("[{0:d}/{1:d}] {2:s} (cached)".format(i, iLen, target_file.name))
            shutil.copyfile(str(dep_files[0]), str(target_file))

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
        soup = BeautifulSoup.BeautifulSoup(file_response.content, 'lxml')
        soup.prettify()
        span = soup.find('span', {'id': 'Download'})
        if span:
            resource = span.a['href']
            link = '{uri.scheme}://{uri.netloc}/{res}'.format(uri=parsed_uri, res=resource)
            file_response = session.get(link, stream=True)
            disable_url = True
        else:
            print('no result')

    content_disposition = file_response.headers.get('Content-Disposition', False)
    if content_disposition:
        file_name = rfc6266.parse_headers(content_disposition).filename_unsafe
    else:
        file_name = file_response.url.rsplit('/', 1)[-1]

    # print('cannot find Content-Disposition header, are you sure this download link is valid?')
        # TODO find filename through alternative methods
        #return None, ''

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

auth_session = None

def authenticate():
    global auth, auth_file, auth_session
    auth_curse = auth.get('curse', None)
    if 'curse' not in auth:
        raise NameError('no_curse_authentication')
    if args.debug:
        print('post https://curse-rest-proxy.azurewebsites.net/api/authenticate')
    r = requests.post('https://curse-rest-proxy.azurewebsites.net/api/authenticate',
                      json=auth_curse)
    r.raise_for_status()
    if r.status_code == 400:
        message = r.json()["message"]
        raise Exception(message)

    if r.status_code == 200:
        response_data = r.json()
        session = response_data["session"]
        global authorization
        authorization = 'Token {0[user_id]}:{0[token]}'.format(session)
        global auth_session
        auth_session = requests.session()
        auth_session.headers.update({'Authorization': 'Token {0[user_id]}:{0[token]}'.format(session)})

def get_add_on(project_id: int) -> Dict[str, Any]:
    global fileCache, auth_session
    project_files = fileCache.get(project_id, None)
    if not project_files:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)
    if not auth_session:
        authenticate()
    if args.debug:
        print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}'
          .format(project_id))
    r = auth_session.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}'
        .format(project_id)
    )
    r.raise_for_status()
    if r.status_code == 200:
        addon = r.json()
        for file in addon['latest_files']:
            project_files[file['id']] = file
        return addon

fileCache = {}


def get_add_on_files(project_id: int) -> List[Dict[str, Any]]:
    global fileCache, auth_session
    project_files = fileCache.get(project_id, None)
    if not project_files:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)
    if not auth_session:
        authenticate()
    if args.debug:
        print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/files'.format(project_id))
    r = auth_session.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/files'
        .format(project_id)
    )
    r.raise_for_status()
    if r.status_code == 200:
        response_data = r.json()
        files = response_data["files"]
        for file in files:
            project_files[file['id']] = file
        return files


def get_add_on_file(project_id: int, file_id: int) -> Dict[str, Any]:
    global fileCache, auth_session
    project_files = fileCache.get(project_id, None)
    if project_files:
        file = project_files.get(file_id, None)
        if file:
            return file
    else:
        fileCache[project_id] = {}
        project_files = fileCache.get(project_id, None)

    if not auth_session:
        authenticate()
    if args.debug:
        print('get https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/file/{1}'.format(project_id, file_id))
    r = auth_session.get(
        'https://curse-rest-proxy.azurewebsites.net/api/addon/{0}/file/{1}'
        .format(project_id, file_id)
    )
    r.raise_for_status()
    if r.status_code == 200:
        file = r.json()
        project_files[file_id] = file

        return file
