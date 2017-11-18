#!/bin/python3
# -*- coding: utf-8 -*-
import codecs
import sys
from .cfutil import *
from .provider import *
from typing import List, Sequence
from pathlib import Path
from shutil import rmtree

print('using encoding {}'.format(sys.stdout.encoding))


# addonData = get_addon_data()

def run():
    # TODO: move into CurseProvider .ctor
    # addonData = get_addon_data()
    # print("data len: {}".format(len(addonData) / (1024.0 * 1024.0)))
    # modnames = [p['name'] for p in addonData]  # if p["PackageType"] == 6]
    # with codecs.open('./modlist.txt', "w", encoding='utf8') as modlist:
    #     modlist.write("\n".join(modnames))

    print(f"config: {config}")
    for pack, packMetaConfig in config["modpacks"].items():
        print(f"name: '{pack}'")
        if not packMetaConfig['enabled']:
            print("skipped")
            continue
        print(yaml.dump(packMetaConfig))
        output_base = Path(config['output'], pack).resolve()
        pack_base = pack  # TODO: file base
        pack_configpath = configDir / 'packs' / f"{pack_base}.yaml"
        defaultpack_configPath = configDir / "pack_default.yaml"
        generatedpack_configPath = configDir / "build" / \
            f"{pack_base}.yaml"  # TODO: make sure directory exists
        generatedpack_configPath.parent.mkdir(parents=True, exist_ok=True)
        # config = yaml.load(configPath.open().read())
        with open(generatedpack_configPath, 'w') as outfile:
            with open(generatedConfigPath) as infile:
                outfile.write(infile.read())
            outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(defaultpack_configPath) as infile:
                outfile.write(infile.read())
            outfile.write('\n# END DEFAULTS\n\n# BEGIN CONFIG\n\n')
            with open(pack_configpath) as infile:
                outfile.write(infile.read())

        with open(generatedpack_configPath, 'r') as f:
            pack_config = yaml.load(f, Loader)

        print(yaml.dump(pack_config))

        pack_name = pack_config.get('name' or pack)
        download_optional = pack_config.get("optionals", False)
        game_version = pack_config.get("mc_version", "1.10.2")
        forge_version = pack_config.get("forge", "recommended")
        default_release_types = pack_config.get('release_type', (RLType.Release, RLType.Beta, RLType.Alpha))

        providers: List[BaseProvider] = []
        providers.append(MavenProvider())
        providers.append(GithubProvider())
        curse_args = (args.debug, download_optional,
                      game_version, default_release_types)
        providers.append(CurseProvider(*curse_args))
        providers.append(DirectProvider())
        providers.append(LocalProvider(Path(output_base, 'local')))


        print('output base {}'.format(output_base))
        mods = pack_config.get("mods", [])
        direct_urls_bool = pack_config.get("urls", True)
        curse_ids = []
        direct_urls = []
        downloads = []

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

        # print(f"entries: \n{yaml.dump(entries)}")

        remove = []
        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            if not provider.prepare_dependencies(entry): #TODO: ranme to filter - something
                remove.append(entry)

        print(f"remove: {yaml.dump(remove)}")
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
        #     print(f"resolve dep entries: \n{yaml.dump(entries)}")

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.fill_information(entry)

        downloaderDirs = appdirs.AppDirs(appname="voodoo", appauthor="nikky")

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.prepare_download(entry, Path(downloaderDirs.user_cache_dir, provider.typ))

        src_path = Path(output_base, 'src')
        
        # resolve full path
        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.resolve_path(entry)
        
        if args.debug:
            print(f"resolve path entries: \n{yaml.dump(entries)}")

        if pack_config.get('urls', True):
            # requires path to be known
            for entry in entries:
                provider: BaseProvider = provider_map[entry['type']]
                provider.write_direct_url(entry, src_path)

        for entry in entries:
            provider: BaseProvider = provider_map[entry['type']]
            provider.write_feature(entry, src_path)

        # if args.debug:
        #     print(f"write urls and features entries: \n{yaml.dump(entries)}")

        loader_path = Path(output_base, 'loaders')
        rmtree(str(loader_path.resolve()), ignore_errors=True)
        loader_path.mkdir(parents=True, exist_ok=True)
        get_forge(forge_version, game_version, loader_path, Path(downloaderDirs.user_cache_dir, 'forge'))

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