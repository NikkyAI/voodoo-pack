import re
from pathlib import Path
from typing import Dict

from jenkinsapi.jenkins import Jenkins

from .BaseProvider import BaseProvider

__all__ = ['JenkinsProvider']


class JenkinsProvider(BaseProvider):
    """
    Downloads Artifacts from jenkins jobs
    """
    
    # optional = ('build_number', 'file_name_regex')
    _required_attributes = ('jenkins_url', 'job')
    _typ = 'jenkins'

    __servers: Dict[str, Jenkins] = {}

    file_name_regex = '.*(?<!-sources\.jar)(?<!-api\.jar)$'

    def validate(self, entry: dict) -> bool:
        return True

    def fill_information(self, entry: dict):
        if 'name' not in entry:
            entry['name'] = entry['job']
        super().fill_information(entry)

    def prepare_download(self, entry: dict, cache_base: Path):
        jenkins_url = entry['jenkins_url']
        job_name = entry['job']
        file_name_regex = entry['file_name_regex']
        server = self.get_server(jenkins_url)
        print(f'[{self._typ.upper()}] get job {job_name}')
        job = server.get_job(job_name)
        if 'build_number' not in entry:
            build_number = job.get_last_stable_buildnumber()
            entry['build_number'] = build_number

        build = job.get_build(entry['build_number'])
        artifact_dict = build.get_artifact_dict()
        p = re.compile(file_name_regex)
        for file_name, artifact in artifact_dict.items():
            if p.fullmatch(file_name):
                entry['url'] = artifact.url
                entry['file_name'] = artifact.filename
                entry['type'] = 'direct'
                break
        if 'cache_base' not in entry:
            entry['cache_base'] = str(cache_base)
        if 'cache_path' not in entry:
            entry['cache_path'] = str(
                Path(entry['cache_base'], *job_name.split('/')))

    def get_server(self, url: str) -> Jenkins:
        server = self.__servers.get(url)
        if not server:
            print(f'[{self._typ.upper()}] get server {url}')
            server = Jenkins(url)
            self.__servers[url] = server
        return server
