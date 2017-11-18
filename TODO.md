register handlers for types: [ curse, github, maven, jenkins, direct, local ]

## split resolve and download
- prepare config

- generate modpack.json

```json
{
  "name" : "example_pack",
  "title" : null,
  "gameVersion" : "1.10.2",
  "features" : [
    {
      "properties" : {
        "name" : "feature name",
        "description" : "feature description",
        "recommendation" : null,
        "selected" : true
      },
      "files" : {
        "include" : [
          "mods/Botania-r1.9-341.870.jar"
        ],
        "exclude" : [ ]
      }
    }
  ],
  "userFiles" : {
    "include" : [
      "options.txt",
      "optionsshaders.txt"
    ],
    "exclude" : [ ]
  },
  "launch" : {
    "flags" : [
      "-Dfml.ignoreInvalidMinecraftCertificates=true"
    ]
  }
}
```

- generate single file features
- generate direct urls

- resolve:
  - resolve_dependencies
    - curse resolves dependencies \
      add optional and required `curse` \
      track `provides`
  - get_urls
    - `curse` -> `direct`
    - github (key?) \
      `curse`, `github` -> `direct`
  - TODO: maven get dependencies ?
  - get metadata from all providers \
    `curse`, `github`, .. description
  - handle optionals / features \
    feature description is curse addon description by default \
    feature-lists include dependencies ?
- build
  - get maven artifact \
  `maven` -> `cached`
- download ( + build ? )
  - download to cache \
    `direct` -> `cached`
  - copy from cache to target \
    `cached` -> `installed`
  - copy local from source to target \
    `local` -> `installed`
  - write optionals / features

- github
- jenkins
  - lastBuild
  - lastStableBuild
  - lastSuccessfulBuild
  - lastFailedBuild
  - lastUnstableBuild
  - lastUnsuccessfulBuild
  - lastCompletedBuild.

