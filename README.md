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

execute `make install-required` or `pip install --user -r requirements.txt` once to install the required packages

execute `make run` or `python -m voodoo` to execute the pack builder

## Configuration

### main config file

example:
`config/config.yaml`

```yaml
authentication: auth.yaml
output: modpacks
modpacks:
  - magical_mayhem.yaml
urls: true
```

- `authentication`: str \
  path to a file containing username and password \
  for `github` \
  you can set username and password through commandline flags though \
  and have no passwords saved in plaintext \
  example: [auth.yaml](config/auth.yaml)
  - optional
  - default: none
- `output`: str \
  path to the output folder for modpacks
  - optional
  - default: `modpacks/`
- `modpacks`: List[str] \
  list of Paths to modpack config files relative to the parent folder of the config file
  - required
- urls: bool \
  enable saving .url.txt files next to the mod jars
  - optional
  - default: `false`

### modpack config files

example:
`config/packs/%modpack%.yaml`

```yaml
name: Example pack

mc_version: "1.12.2"

optionals: true
# this adds also optiona dependencies from curse and other sources

forge: "1.12.2" # `version`(-recommended /-latest) or branch-name

urls: true
release_type:
  - Release
  - Beta
  - Alpha

asie_mod_archive: &asie_mod_archive: https://asie.pl/files/mods/

mods:

  - <<: *curse # it a curse mod
    name: Quark

  - Baubles # just the curse mod name works as well

  - <<: [*mvn, *feature] # not yet integrated
    remoteRepository: "http://mvn.rx14.co.uk/local/"
    group: vazkii.botania
    artifact: Botania
    version: "r1.9-341.870"
    # feature properties
    description: "test - feature descriotion" # i hope i can get this from maven eventually
    selected: false
    recommendation: "starred" # starred or avoid

  - <<: *github # not yet integrated
    user: copygirl
    repo: WearableBackpacks
    tag: v1.1.0.2-beta

  - <<: *direct
    url: !join [*asie_mod_archive, Charset/Charset-0.5.0.79.jar] # join strings

  - <<: *direct
    url: !join [*asie_mod_archive, FoamFix/foamfix-0.8.1-1.12-anarchy.jar]

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
- <<: [*featue, *curse]
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

start the entry with the merge key `<<:` referencing anchors for the different mod types

```yaml
- <<: *curse
  name: JourneyMap
  mc_version: 1.9
```

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
- `release_type` List[str]
  - optional
  - values:
    - `Release`
    - `Beta`
    - `Alpha`

`name` or `project_id` are required

###### jenkins

TODO: implement and update doc

example:

```yaml
- jenkins:
    remoteRepository: http://ci.tterrag.com/
    name: Chisel
    branch: 1.10/dev
```

keys:

- `remoteRepository`: str
- `name`: str
- `branch_id`: str
  - optional
  - default: `master`
- `build_type`: str
  - optional
  - default: `lastStableBuild`
  - values:
    - `lastBuild`
    - `lastStableBuild`
    - `lastSuccessfulBuild`
    - `lastFailedBuild`
    - `lastUnstableBuild`
    - `lastUnsuccessfulBuild`
    - `lastCompletedBuild.`

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

the target must serve the filename with a Content-Disposition Header for now or `file_name_on_disk` is specified

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
- `file_name_on_disk`: str
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
