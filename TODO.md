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

- packageType: folder, singlefile
  - folder: uncompress
  - singlefile

- improve cache system
  - copy into target filename

- support mc_version list \
  or support version startswith mc_version

- generate multi file features

- duplicate checks, priority by order \
  done in curse


- github
- jenkins
  - lastBuild
  - lastStableBuild
  - lastSuccessfulBuild
  - lastFailedBuild
  - lastUnstableBuild
  - lastUnsuccessfulBuild
  - lastCompletedBuild.
- maven
