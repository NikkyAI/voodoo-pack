# curseforge-pack-builder (name subject to change)
a utility to create modpacks for sklauncher
and download mods from curseforge and other sources
with minimal configuration

## Features

downloads mods from
- `curse`forge
- `jenkins`
- `github` releases
- `direct` urls

downloads dependencies for curse mods

supports clientside / serverside mods

supports optional mods

caches downloaded mods to avoid redownloading for `curse`, `jenkins` and `github`

## setup and execution

execute `setup.sh` or `setup.bat` once to install the required packages

execute `run.sh` or `run.bat` to build the packs

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

- `authetication`: str   
  path to a file containing username and password   
  for `curse` and `github`   
  you can set username and password though commandline flags though and have no password saved in plaintext
  example: [auth.yaml](config/auth.yaml)   
  - optional
  - default: none
- `output`: str   
  path to the output folder for modpacks
  - optional
  - default: `modpacks/`
- `modpacks`: List[str]   
  list of Paths to modpack config files relative to the parent folder of the config file
  - required
- urls: bool   
  enable saving .url.txt files next to the mod jars
  - optional
  - default: `false`

### modpack config files
example:
`config/%modpack%.yaml`

```yaml
output: "../../minecraft/modpackcreator/modpacks/magical_mayhem/src/" #realtive or abslute path
mcversion: 1.10.2
optionals: true # refers to curseforge optional dependencies
release_type:
- Release
- Beta
- Alpha
mods:
- name: JourneyMap
  version: map-1.10.2
  release_type:
  - Release
  - Beta
- curse: Applied Energistics 2
  side: client #goes into mods/_CLIENT/
- direct: https://github.com/copygirl/BetterStorage/releases/download/v0.13.1.127/BetterStorage-1.7.10-0.13.1.127.jar
  feature:
   # https://github.com/SKCraft/Launcher/wiki/Optional-Features#via-infojson-files
    description: this is the wrong version, but Wearablebackpacks is not done yet
    recommendation: none # | starred | avoid
    selected: false
- github: copygirl/BetterStorage
- 228756
- curse: Chisel
  side: both # goes into mods/ also the default anyway
- direct: http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
  side: client # goes into mods/_CLIENT
- Extra Utilities
```

- `output`: str
  - default: `modpack/`
  - info: this has to match with the src folder in from the creatortools 
- `mc_version`: str
  - optional
  - default: `1.10.2`
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
- name: JourneyMap
  version: map-1.10.2
  release_type:
  - Release
  - Beta
  mc_version: '1.10.2'
  side: client
  feature:
    description: Minimap
    recommendation: starred
    selected: true
```

a entry can be

- int (see short forms [id](#id))
- string (see short forms [name](#name) and [user/repo](#userrepo))
- dict

##### short forms

###### id
`- 228756` –> `- project_id: 228756`   
`- curse: Extra 228756` –> `- project_id: 228756`

###### name
`- Extra Utilities` –> `- name: Extra Utilities`   
`- curse: Extra Utilities` –> `- name: Extra Utilities`

###### user/repo
```yaml
- github: copygirl/WearableBackpacks
``` -> 
```yaml
- github
    user: copygirl
    repo: WearableBackpacks
```

###### dict
if the entry does not contain one of the type keys `curse`, `github`, `jenkins`, `direct`
the entry will be treated as type `curse`

```yaml
- name: JourneyMap
  mc_version: 1.9
``` 
is equal to
```yaml
- curse
    name: JourneyMap
    mc_version: 1.9
```

##### types

###### curse

example:
```yaml
- curse
    name: Extra Utilities
```
```yaml
- name: Extra Utilities
```
keys: 
- `curse`: dict
    - `name`: str
    - `project_id`: int
    - `mc_version`: str
      - optional
    - `version`: str
      - optional
      - check if `version` is in the filename 
    - `release_type` List[str]
      - optional
      - values:
        - `Release`
        - `Beta`
        - `Alpha`

`name` or `project_id` are required

###### jenkins 

example:
```yaml
- jenkins:
    url: http://ci.tterrag.com/
    name: Chisel
    branch: 1.10/dev
```

keys: 
- `jenkins`: dict
    - `url`: str
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
example:
```yaml
- github: copygirl/WearableBackpacks
- github: copygirl/BetterStorage
    tag: v0.13.1.127
- github:
    user: copygirl
    repo: BetterStorage
    tag: v0.13.1.127
```

keys: 
- `github`: dict
    - `user`: str
    - `repo`: str
    - `tag`: str
      - optional
      - default: `ǹone` 


###### direct

example:
```yaml
- direct: http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
```
the target must serve the filename in a Content-Disposition Header for now  

keys:

- `direct`: str
    url


##### side

changes the folder for the mod to `_CLIENT` or `_SERVER`

keys: 

- `side`: str
  - values:
    - `client`
    - `server`

see [SKCraft/Launcher/wiki/Creating-Modpacks#marking-files-client-or-server-only](https://github.com/SKCraft/Launcher/wiki/Creating-Modpacks#marking-files-client-or-server-only)

##### optinal features

saves a .info.json file alongside the mod

example: 
```yaml
feature:
  description: Minimap
  recommendation: starred
  selected: true
```

keys:

- `feature`: dict
  - `name`: str
    - optional
    - default: `projectname` or `filename`
  - `description`: str
    - optional
  - `recommendation`: bool
    - values
      - `starred`
      - `avoid`
  - `selected`: bool
    - values 
      - `true`
      - `false`

see [SKCraft/Launcher/wiki/Optional-Features#via-infojson-files](https://github.com/SKCraft/Launcher/wiki/Optional-Features#via-infojson-files)