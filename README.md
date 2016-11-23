# curseforge-pack-builder (name subject to change)
a utility to create modpacks for sklauncher
and download mods from curseforge and other sources
with minimal configuration

## Features

downloads mods from
- curse
- urls
- github (NYI)

downloads dependencies for curse mods

supports clientside / serverside mods

supports optional mods

## setup and execution

execute `setup.sh` or `setup.bat` once to install the required packages
execute `run.sh` or `run.bat`

## Configuration
### main config file 
`config/config.yaml`
example:

```yaml
authentication: auth.yaml
output: modpacks
modpacks:
  - magical_mayhem.yaml
urls: true
```
#### authentication:
    path to a file containing
    
    ```yaml
    username: login
    password: password
    ```

#### output
    path to the default modpack output folder
    default value: `modpacks`

#### modpacks
    list of modpack config files in `config/`

#### urls
    decides to save a .url.txt file next to the downloaded files
    
    
### modpack config files
`config/%modpack%.yaml`
example:

```yaml
output: "../../minecraft/modpackcreator/modpacks/magical_mayhem/src/"
mcversion: 1.10.2
optionals: true
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
- github: copygirl/BetterStorage # NYI
- 228756
- curse: Chisel
  side: both # goes into mods/
- direct: http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
  side: client # goes into mods/_CLIENT
- Extra Utilities
```

#### output
- `output`: str
    default: `modpack/`
    this has to match with the src folder in from the creatortools 
    
- `mc_version`: str
    default: `1.10.2`

- `optionals`: bool
    download optional dependencies of curseforge mods
    default: `true`
    
- `release_type` List[str]
    optional
    default: `Release`, `Beta`
    values:
      - `Release`
      - `Beta`
      - `Alpha`
    example:
    ```yaml
    - Alpha
    - Beta
    ```


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

- int (see short forms id)
- string (see short forms name)
- dict

###### short forms

id:
```- 228756``` –> ```- project_id: 228756```
```- curse: Extra 228756``` –> ```- project_id: 228756```

name:
```- Extra Utilities``` –> ```- name: Extra Utilities```
```- curse: Extra Utilities``` –> ```- name: Extra Utilities```

##### types

###### cursefurge / curse

example:
```yaml
- name: Extra Utilities
```
keys: 

- `name`: str
- `project_id`: int
- `mc_version`: str
    optional
- `version`: str
    optional
    check if `version` is in the filename 
- `release_type` List[str]
    optional
    values:
      - `Release`
      - `Beta`
      - `Alpha`

`name` or `project_id` are required
    
###### direct

example:
```yaml
- direct: http://optifine.net/adloadx?f=OptiFine_1.10.2_HD_U_D2.jar
```
the target must serve a Content-Disposition Header   

keys:

- `direct`: str
    url
    
###### github 
(NYI)

##### side

changes the folder for the mod to `_CLIENT` or `_SERVER`

keys: 

- `side`: str
    - values:
        - `client`
        - `server`

see https://github.com/SKCraft/Launcher/wiki/Creating-Modpacks#marking-files-client-or-server-only

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

- `feature`
    - `name`: 
      optional
      default: `projectname` or `filename`
    - `description`: 
      optional
    - `recommendation`
      values:   
        - `starred`
        - `avoid`
    - `selected`: 
    values: 
        - `true`
        - `false`

see https://github.com/SKCraft/Launcher/wiki/Optional-Features#via-infojson-files