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

- generate multi file features

- duplicate checks, priority by order

- allow defining dependencies manually

- dependency graph
  - grouping for features
  - grouping for features

- resolve:
  - resolve_dependencies
    - curse resolves dependencies \
      add optional and required `curse` \
      track `provides`
  - get_urls
    - `curse` -> `direct`
    - `jenkins` -> `direct`
    - github (key?) \
      `github` -> `direct`
  - TODO: maven get dependencies ?
  - get metadata from all providers \
    `curse`, `github`, .. description
  - handle optionals / features \
    feature description is curse addon description by default \
    feature-lists include dependencies ?
- build
- download ( + build ? )
  - download (cached) \
    `direct` -> `done`
  - get maven artifact \
    `maven` -> `done`
  - copy local from source to target \
    `local` -> `done`
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

