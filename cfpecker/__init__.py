#!/bin/python3
# -*- coding: utf-8 -*-
import codecs
import sys

print('using encoding {}'.format(sys.stdout.encoding))

from .cfutil import *
ProjectData = get_project_data()

def run():
    print("data len: {}".format(len(ProjectData) / (1024.0 * 1024.0)))
    modnames = [p['Name'] for p in ProjectData if p["PackageType"] == 6]
    with codecs.open('./modlist.txt', "w", encoding='utf8') as modlist:
        modlist.write("\n".join(modnames))

    for packConfig in config["modpacks"]:
        print(packConfig)
        modpackDir = packConfig['output']

        modpackFolder = Path(modpackDir)
        print('modpack output {}'.format(modpackFolder))
        defaultGameVersion = packConfig.get("mc_version", "1.10.2")
        default_release_types = packConfig.get('release_type', (RLType.Release, RLType.Beta, RLType.Alpha))
        mods = packConfig.get("mods", [])
        download_optional = packConfig.get("optionals", False)
        direct_urls_bool = packConfig.get("urls", True)
        curse_ids = []
        direct_urls = []
        downloads = []

        for mod in mods:
            curse_parameter = None
            download_parameter = {}
            print("type: {} : {}".format(type(mod), mod))
            if isinstance(mod, str):
                curse_parameter = {'name': mod}
            elif isinstance(mod, int):
                curse_parameter = {'project_id': mod}
            elif isinstance(mod, dict):
                if args.debug:
                    print('downloading\n\t{}'.format(mod))

                # side and feature
                # TODO clean up by copying values
                side = mod.get('side', False)
                if side:
                    download_parameter['side'] = side
                feature = mod.get('feature', False)
                if feature:
                    download_parameter['feature'] = feature

                if 'direct' in mod:
                    # direct download url
                    print(type(mod['direct']))
                    direct_urls.append({'direct': mod['direct']})
                    download_parameter['direct'] = mod['direct']
                    download_parameter['type'] = 'direct'

                elif 'github' in mod:
                    # github download id
                    # name/repo
                    github_parameter = None
                    github = mod['github']
                    if isinstance(mod['github'], dict):
                        github_parameter = mod['github']
                    elif isinstance(mod['github'], str):
                        user_repo = mod['github'].split('/', 1)
                        if len(user_repo) == 2:
                            user = user_repo[0]
                            repo = user_repo[1]
                            github_parameter = {'user': user, 'repo': repo}
                            if 'tag' in mod:
                                github_parameter['tag'] = mod['tag']
                    if github_parameter:
                        download_parameter['type'] = 'github'
                        download_parameter['github'] = github_parameter

                elif 'jenkins' in mod:
                    # name/job
                    jenkins = mod['jenkins']
                    if isinstance(mod['jenkins'], dict):
                        if 'url' not in jenkins:
                            print('no jenkins url')
                            continue
                        if 'name' not in jenkins:
                            print('no name (job) provided')
                            continue

                        download_parameter['type'] = 'jenkins'
                        download_parameter['jenkins'] = jenkins

                    else:
                        print('unknown data {}'.format(jenkins))
                        continue


                elif 'maven' in mod:
                    # group_id / artifact_id / version
                    maven = mod['maven']
                    if isinstance(maven, dict):
                        if 'group' not in maven:
                            print('no group_id provided')
                            continue
                        if 'artifact' not in maven:
                            print('no artifact_id provided')
                            continue
                        if 'version' not in maven:
                            print('no version provided')
                            continue

                        download_parameter['type'] = 'mvn'
                        download_parameter['mvn'] = maven

                    else:
                        print('unknown data {}'.format(maven))
                        continue

                elif 'local' in mod:
                    # group_id / artifact_id / version
                    local = mod['local']

                    if isinstance(local, str):
                        if not local:
                            print('no file specified')
                            continue

                        download_parameter['type'] = 'local'
                        download_parameter['local'] = { 'local_file': local}
                    else:
                        print('unknown data {}'.format(local))
                        continue


                elif 'curse' in mod:
                    if isinstance(mod['curse'], dict):
                        curse_parameter = mod['curse']
                    elif isinstance(mod['curse'], str):
                        curse_parameter = {'name': mod['curse']}
                    elif isinstance(mod['curse'], int):
                        curse_parameter = {'project_id': mod['curse']}
                    else:
                        continue
                else:
                    curse_parameter = {
                        key: mod[key] for key
                        in ['name', 'mc_version', 'version', 'release_type', 'optional']
                        if key in mod
                        }
                    print('curse\t{}'.format(curse_parameter))

                if 'optional' in mod:
                    download_parameter['optional'] = mod['optional']

            else:
                print('unknown: {}'.format(mod))

            if curse_parameter:
                project_id, file_id, file_name = find_curse_file(**curse_parameter)
                if project_id > 0 and file_id > 0:
                    curse_ids.append((project_id, file_id))
                    download_parameter['curse'] = {'project_id': project_id, 'file_id': file_id}
                    download_parameter['type'] = 'curse'
                else:
                    print("cannot find:")
                    for k, v in curse_parameter.items():
                        print('\t{}: {}'.format(k, v))
                    continue

            # print(mod)
            if download_parameter:
                downloads.append(download_parameter)
            else:
                print('error with: {}'.format(mod))
                print(type(mod))

        download(modpackFolder, download_list=downloads, curse_optional=download_optional, direct_urls=direct_urls_bool)
