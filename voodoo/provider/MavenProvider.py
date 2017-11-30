from pathlib import Path
from urllib.parse import quote, unquote, urljoin, urlparse, urlunsplit

import requests
import xmltodict

from .BaseProvider import BaseProvider

__all__ = ['MavenProvider']


class MavenProvider(BaseProvider):
    _required_attributes = (
        'remote_repository', 'group', 'artifact', 'version', 'path', 'package_type'
    )
    _typ = 'mvn'

    def prepare_dependencies(self, entry: dict):
        remote_repository = entry.get('remote_repository')
        if not remote_repository[-1] == '/':
            remote_repository += '/'
        group = entry.get('group').replace('.', '/')
        artifact = entry.get('artifact')
        version = str(entry.get('version', 'release'))
        path = '/'.join([*group.split('.'), artifact, 'maven-metadata.xml'])
        url = urljoin(remote_repository, path)
        response = requests.get(url)
        response.raise_for_status()
        meta = xmltodict.parse(response.content)
        if version == 'release':
            version = meta['metadata']['versioning'].get('release')
            if not version:
                version = meta['metadata'].get('version')
            assert version, f'no release or default version could be found for {artifact}'
        else:
            versions = meta['metadata']['versioning']['versions']['version']
            # filter versions # TODO: regex
            versions = [v for v in versions if version in v]
            assert versions, f'{version} not found in {url}'
            version = sorted(versions)[-1]
            print(versions)
            print(version)
        entry['version'] = version
        print(f'{artifact} version is {version}')

    def validate(self, entry: dict) -> bool:
        # TDOD: check if version was found
        return True

    def fill_information(self, entry: dict):
        if 'name' not in entry:
            entry['name'] = entry['artifact']
        super().fill_information(entry)
    
    def prepare_download(self, entry: dict, cache_base: Path):
        remote_repository = entry.get('remote_repository')
        group = entry.get('group')
        artifact = entry.get('artifact')
        version = entry.get('version')

        file_name = f"{artifact}-{version}.jar"
        path = '/'.join([*group.split('.'), artifact, version, file_name])
        url = urljoin(remote_repository, str(path))

        entry['type'] = 'direct'
        entry['url'] = url
        entry['file_name'] = file_name

        if 'cache_base' not in entry:
            entry['cache_base'] = str(cache_base)
        if 'cache_path' not in entry:
            entry['cache_path'] = str(
                Path(entry['cache_base'], *group.split('.'), artifact, version, file_name))
