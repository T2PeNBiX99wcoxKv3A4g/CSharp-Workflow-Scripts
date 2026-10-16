# Version Change Workflow Scripts

`CSharp-Workflow-Scripts` is a legacy name that no longer means anything; the
scripts are not C#-specific and can be used anywhere.

They are mostly used in my GitHub repositories to bump versions automatically.

## change_version.py

### `change-version`

Detects the current version in a file and replaces it with a new one.

```shell
python change_version.py change-version <file_path> <version_key> <new_version> [OPTIONS]
```

| Option               | Description                                                |
|----------------------|------------------------------------------------------------|
| `--require-keywords` | Comma-separated keywords that the target line must contain |
| `--debug`            | Enable `icecream` debug output                             |

`version_key` is a complete key name, matched case-sensitively, so `Version`
never matches `AssemblyVersion` or `<SupportedOSPlatformVersion>`. The value
follows a separator (`=`, `:`, `>` or `(`) with an optional surrounding quote, so
`version = "1.2.3"`, `"Version": "1.2.3"` and `<Version>1.2.3</Version>` all work.
Lines that start with a comment marker (`#`, `!`, `//`, `<!--`, `;`) are skipped.

The version is detected on the first matching line and then replaced **only on
lines whose key matches**, so no other line is touched. Every matching line is a
target, which handles a version that lives in several places at once. A matching
key whose value is a *different* version is left alone, so `Version="10.0.13"` in
a `PackageReference` is not clobbered when the project version is `0.1.0`.

If no line is replaced the command fails instead of reporting a successful bump,
so a version that is already current is an error rather than a silent no-op.

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
python change_version.py Properties/AssemblyInfo.cs AssemblyVersion 0.2.0.0
```

### `replace-version`

`change-version` also writes the detected old version to `./.version_old` and the
new one to `./.version`, both in the current working directory. `replace-version`
reuses that pair to update any other file, which keeps secondary files in sync.

```shell
python change_version.py change-version App.csproj Version 0.2.0
python change_version.py replace-version README.md
```

Without `--version-key` it replaces every occurrence, which is what documentation
files such as `README.md` need. A file that does not mention the version is
reported but does not fail. Pass `--version-key` to limit the replacement to
lines whose key matches instead, in which case a file with no matching line is an
error.

```shell
python change_version.py replace-version manifest.json --version-key version
```

### `create-version-file`

`create-version-file` only writes `./.version`. Use it when the new version comes
from somewhere else, such as a git tag. It normalizes the version the same way
`change-version` does, so `v1.2.3` becomes `1.2.3`. It does not write
`./.version_old`, so `replace-version` still needs a `change-version` run first.

```shell
python change_version.py create-version-file "v1.2.3"
```

### GitHub Actions outputs

When `GITHUB_OUTPUT` is set, the commands export these step outputs:

| Command               | Outputs                      |
|-----------------------|------------------------------|
| `change-version`      | `old_version`, `new_version` |
| `create-version-file` | `new_version`                |

## get_version.py

### `get-version`

Fetches a URL and exports the response body as the `get_version` step output. The
script has a single command, so it is called without a subcommand.

```shell
python get_version.py https://example.com/version.txt
```

| Option    | Description                    |
|-----------|--------------------------------|
| `--debug` | Enable `icecream` debug output |
