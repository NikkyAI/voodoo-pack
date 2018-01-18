## Fix

Warning: node OTG, port  Skylands unrecognized
Warning: node OTG, port  The Void unrecognized

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

- better config merging \
  recursive merging for keys that are both dicts, override for mismatched types

- dump defaults for each provider next to package_type.yaml

- packageType: folder, singlefile
  - folder: uncompress
  - singlefile

- improve cache system
  - keep etag or filehash

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
