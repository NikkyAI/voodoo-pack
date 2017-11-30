# voodoo-pack

a utility to create modpacks for sklauncher
and download mods from curseforge and other sources
with minimal (and hhopefully intuitive) configuration

## Features

downloads mods from

- `curse`forge
- `jenkins`
- `github` releases
- `direct` urls
- `local` no real download i guess

downloads dependencies for curse mods

supports clientside / serverside mods

supports optional mods

caches downloaded mods to avoid redownloading for `curse`, `jenkins` and `github`

## setup and execution

install graphviz

execute `make install-required` or `pip install --user -r requirements.txt` once to install the required packages

execute `make run` or `python -m voodoo` to execute the pack builder

## linux

**recommended**

1. install python 3.6+
2. install graphviz
3. download the latest source \
  ```sh
  git -c voodoo-pack pull || git clone https://github.com/NikkyAI/voodoo-pack.git
  cd voodoo-pack
  ```

### user install
  ```sh
  pip uninstall -y voodoo
  pip install --user .
  ```

### virtualenv install

install python-virtualenv

4. execute the comamnds \
  ```sh
  virtualenv virtualenv
  source virtualenv/bin/activate
  pip uninstall -y voodoo
  pip install .
  ```

4. copy the defaults and start working \
  ```sh
  PACKDEV='~/dev/modpacks'
  mkdir -p $PACKDEV
  cp -r config $PACKDEV
  cd $PACKDEV
  voodoo
  ```

## windows

**not recommended** for general usage due to requiring graphviz binaries to be on the PATH, and maybe otherwindows things that can mess up

1. install python https://www.python.org/ftp/python/3.6.3/python-3.6.3.exe
2. install graphviz and make sure its on the path \
   https://graphviz.gitlab.io/_pages/Download/Download_windows.html
2. download the latest version of the repo \
   `git clone https://github.com/NikkyAI/voodoo-pack.git`
3. install \
   `pip uninstall -y voodoo && pip install .`
4. run in some othert directory \
   `voodoo`

## Configuration

### main config file

example:
`config/config.yaml`

```yaml
modpacks: # TODO: turn into list
  "example_pack":
    <<: *modpack
  "testpack":
    <<: *modpack
    name: renamed pack
  "unusedpack":
    <<: *modpack
    name: disabled pack
    enabled: false
output: modpacks
urls: true
```

- `packs`: str \
  path to the config directory of modpacks
  - optional
  - default: `packs/`

- `modpacks`: Dict[str, overrides] \
  list of modpack names and overrides that will be applied \
  to the pack config, allows to change versions or override `enabled`
  - required

following properties can be set in `config.yaml` or `{pack_name}.yaml` **and may be overridden**

- `enabled`: bool \
  skips the pack when set to `false`
  - optional
  - default: `true`

- `output`: str \
  path to the output folder for modpacks
  - optional
  - default: `modpacks/`

- `data_path`: str \
  path to the data dump directory for each pack \
  is used for dependency graphs, info about defaults etc..
  - optional
  - default: `data/`

- `temp_path`: str \
  path to the merged configs folder \
  will not be written if value is `null` or `false`
  - optional
  - default: `null`

- `urls`: bool \
  enable saving .url.txt files next to all files that can be downloaded directly
  - optional
  - default: `true`

- `mc_version`: List[str] or str \
  list of one or more minecraft versions that will be used by eg. curse and forge to find the correct files
  - required
  - default: `1.12.2`

- `sponge`: str \
  sponge forge version
  - optional
  - default: `null`
  - values
    - `release`
    - version

- `forge`: str or int \
  forge version \
  settings other than `recommended`, `latest` or a build_number \
  are possible but not recommended
  - optional
  - default: `recommended`
  - values
    - `recommended`
    - `latest`
    - build_number \
      eg: `2491`
    - branch-name
    - version
    - promo

- `provider_settings` \
    see generated file `defaults.yaml` in the data directory

  - `curse` \
    - `optional`: bool \
      adds optional addons to the modpack when resolving dependencies
      - default: `false`

    - `release_types`: List[str] \
      configures which release types of files are being accepted
      - default: `[Release, Beta]`

    - `meta_url`: str \
      base url of the used cursemeta instance \
      host your own: https://github.com/NikkyAI/cursemeta
      - default: `https://cursemeta.nikky.moe`

    - `dump_data`: bool \
      enable dumping addon data into the data directory
      - default: `true`

  - `local`
    - `folder`: str \
      base directory that local files are loaded from \
      if the file is not specified with a absolute path
      - default: `local`

### modpack config files

example:
`config/packs/%modpack%.yaml`

```yaml
name: Example pack

mc_version: "1.12.2"

sponge: release
#forge: "latest" # `version`(-recommended /-latest) or branch-name

urls: true

provider_settings:
  curse:
    <<: *curse_settings
    optional: false
    release_types:
      - Release
      - Beta
      - Alpha

  local:
    <<: *local_settings
    folder: local

mods:

  - <<: *curse # it a curse mod
    name: Quark

  - Baubles # just the curse mod name works as well

  - <<: [*mvn]
    remote_repository: 'http://maven.covers1624.net'
    group: cofh
    artifact: ThermalDynamics
    version: 1.12

  - <<: *github # not yet integrated
    user: copygirl
    repo: WearableBackpacks
    tag: v1.1.0.2-beta

  - <<: *direct
    url: !join https://asie.pl/files/mods/FoamFix/foamfix-0.8.1-1.12-anarchy.jar

  - <<: [*curse, *client, *feature]
    name: "NoNausea"
    # description: No puking # dscription is loaded by curse
    recommendation: "starred"
    selected: true

  - <<: *local
    file: OptiFine_1.12.2_HD_U_C6.jar
```

- `output`: str
  - default: `modpacks`
  - info: this has to match with the src folder from the creatortools
- `mc_version`: str
  - optional
  - default: `1.10.2` TODO: latest recommended forge version
- `optionals`: bool
  - info: download optional dependencies of curseforge mods
  - optional
  - default: `true`
- `release_type` List[str]
  - optional
  - default: `Release`, `Beta`
  - values:
    - `Release`
    - `Beta`
    - `Alpha`
  - example:
    ```yaml
    - Alpha
    - Beta
    ```
  - mods: List

  see [mods](#mods)

#### mods

list of entries

example entries

```yaml
- <<: [*feature, *curse]
  name: JourneyMap
  version: map-1.10.2
  release_type:
  - Release
  - Beta
  mc_version: '1.10.2'
  side: client
  # description: Minimap # is loaded from curse
  recommendation: starred
  selected: true
```

a entry can be

- int (see short forms [id](#id))
- string (see short forms [name](#name) and [user/repo](#userrepo))
- dict

##### short forms

###### id

`- 228756` –> `- addon_id: 228756`

###### name

`- Extra Utilities` –> `- name: Extra Utilities`

###### user/repo

NOT YET IMPLEMENTED
TODO:

`- copygirl/WearableBackpacks` -->

```yaml
- <<: *github
  user: copygirl
  repo: WearableBackpacks
```

###### dict

start the entry with the merge key `<<:` referencing anchors for the different entry types

```yaml
- <<: *curse
  name: JourneyMap
  mc_version: 1.9
```
##### general properties

these keys are set and can be overriden on every entry
ALL of them are optional and will be inferred from other values or the providers

keys: 

- `path`: str \
  folder that the file will be saved to \
  - default: `mods`
- `package_type`: str
  - values
    - `mod`
    - TODO: add support for others eg. worlds, texturepacks
- `name`: str

##### types

###### curse

example:

```yaml
- <<: *curse
  name: Extra Utilities
```

keys:

- `name`: str
- `addon_id`: int
- `file_id`: int
  - optional
  - skips curse file search
- `mc_version`: str
  - optional
- `version`: str
  - optional
  - checks if `version` is in the filename
- `release_types` List[str]
  - optional
  - values:
    - `Release`
    - `Beta`
    - `Alpha`

`name` or `addon_id` are required

###### jenkins

example:

```yaml
- <<: *jenkins
  jenkins_url: https://ci.elytradev.com
  job: elytra/FruitPhone/1.12
```

keys:

- `jenkins_url`: str
- `job`: str
- `file_name_regex` : str
  - optional
  - default: `.*(?<!-sources\.jar)(?<!-api\.jar)$`
- `build_number`: int
  - optional

###### github

TODO: implement and update doc

example:

```yaml
- copygirl/WearableBackpacks/v0.13.1.127
- <<: *github:
    user: copygirl
    repo: BetterStorage
    tag: v0.13.1.127
```

keys:

- `user`: str
- `repo`: str
- `tag`: str
  - optional
  - default: latest release

###### direct

TODO: implement string matching and conversion

example:

```yaml
- <<: *direct:
  url: http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
- http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
```

~~the target must serve the filename with a Content-Disposition Header for now or~~ `file_name` is specified or filename is parsed from url

keys:

- `url`: str
    url

###### local

expects files to be in

```bash
$output/'src'/'local'
```

or be absolute paths

example:

```yaml
- <<: *local:
  fiile: HardcoreDarkness-MC1.11-1.8.1.jar
```

keys:

- `file`: str
- `file_name`: str
  - optional

##### side

changes the folder for the mod to `_CLIENT` or `_SERVER`

example:

```yaml
- <<: [*curse, *client]
  name: "NoNausea"

- <<: [*curse, *server]
  name: "Thumpcord"
```

see [SKCraft/Launcher/wiki/Creating-Modpacks#marking-files-client-or-server-only](https://github.com/SKCraft/Launcher/wiki/Creating-Modpacks#marking-files-client-or-server-only)

##### optinal features

saves a .info.json file alongside the mod

example:

```yaml
- <<: [ *curse, *feature]
  name: JourneyMap
  description: Minimap # cane be filled by curse if left empty
  recommendation: starred
  selected: true
```

keys:

- `name`: str
  - optional
  - default: `addonName` or `filename`
- `description`: str
  - optional
- `recommendation`: str
  - optional
  - values
    - `starred`
    - `avoid`
- `selected`: bool
  - values
    - `true`
    - `false`

see [SKCraft/Launcher/wiki/Optional-Features#via-infojson-files](https://github.com/SKCraft/Launcher/wiki/Optional-Features#via-infojson-files)
