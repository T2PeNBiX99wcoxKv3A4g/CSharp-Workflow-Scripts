# C# Workflow Scripts

Simple python scripts for my github repositories

## change_version.py

### `change-version`

Detect the current version in a file and replace it with a new one.

```shell
python change_version.py change-version <file_path> <version_key> <new_version> [OPTIONS]
```

| Option               | Description                                                |
|----------------------|------------------------------------------------------------|
| `--require-keywords` | Comma separated keywords the target line must also contain |
| `--debug`            | Enable `icecream` debug output                             |

`version_key` is the complete key name, matched case-sensitively, so `Version`
never matches `AssemblyVersion` or `<SupportedOSPlatformVersion>`. The value is
taken after an optional quote and an `=`, `:`, `>` or `(` separator, and comment
lines (`#`, `!`, `//`, `<!--`, `;`) are skipped.

```shell
# csproj:            <Version>0.1.0</Version>
python change_version.py App.csproj Version 0.2.0

# JVM properties:    version=0.1.0
python change_version.py gradle.properties version 0.2.0

# thunderstore.toml: versionNumber = "0.1.0"
python change_version.py thunderstore.toml versionNumber 0.2.0

# JSON:              "Version": "0.1.0"
python change_version.py manifest.json Version 0.2.0

# C#:                [assembly: AssemblyVersion("0.1.0.0")]
python change_version.py Properties/AssemblyInfo.cs AssemblyVersion 0.2.0
```

### `replace-version` / `create-version-file`

`change-version` also records the detected old version in `./.version_old` and
the new one in `./.version`. `replace-version` reuses that pair to update any
other file, which keeps secondary files in sync.

```shell
python change_version.py change-version App.csproj Version 0.2.0
python change_version.py replace-version README.md
```

`create-version-file` only writes `./.version`, for when the new version comes
from somewhere else such as a git tag.

```shell
python change_version.py create-version-file "v1.2.3"
```
