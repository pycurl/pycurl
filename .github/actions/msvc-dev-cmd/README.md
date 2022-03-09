<a href="https://github.com/ilammy/msvc-dev-cmd"><img alt="GitHub Actions status" src="https://github.com/ilammy/msvc-dev-cmd/workflows/msvc-dev-cmd/badge.svg"></a>

# msvc-dev-cmd

[GitHub Action](https://github.com/features/actions) for configuring Developer Command Prompt for Microsoft Visual C++.

This sets up the environment for compiling C/C++ code from command line.

Supports Windows. Does nothing on Linux and macOS.

## Example usage

Basic usage for default compilation settings is like this:

```yaml
jobs:
  test:
    steps:
      - uses: actions/checkout@v2
      - uses: ilammy/msvc-dev-cmd@v1
      - name: Build something requiring CL.EXE
        run: |
          cmake -G "NMake Makefiles" .
          nmake
      # ...
```

If you want something non-default,
like using a specific version of Visual Studio,
or cross-compling for a differen target,
you will need to configure those settings via inputs:

```yaml
jobs:
  test:
    # Run a job for each of the specified target architectures:
    strategy:
      matrix:
        arch:
          - amd64
          - amd64_x86
          - amd64_arm64
    steps:
      - uses: actions/checkout@v2
      - uses: ilammy/msvc-dev-cmd@v1
        with:
          arch: ${{ matrix.arch }}
      - name: Build something requiring CL.EXE
        run: |
          cmake -G "NMake Makefiles" .
          nmake
      # ...
```

## Inputs

- `arch` – target architecture
  - native compilation:
    - `x64` (default) or its synonyms: `amd64`, `win64`, `x86_64`, `x86-64`
    - `x86` or its synonyms: `win32`
  - cross-compilation: `x86_amd64`, `x86_arm`, `x86_arm64`, `amd64_x86`, `amd64_arm`, `amd64_arm64`
- `sdk` – Windows SDK to use
  - do not specify to use the default SDK
  - or specify full Windows 10 SDK number (e.g, `10.0.10240.0`)
  - or write `8.1` to use Windows 8.1 SDK
- `toolset` – select VC++ compiler toolset version
  - do not specify to use the default toolset
  - `14.0` for VC++ 2015 Compiler Toolset
  - `14.XX` for the latest 14.XX toolset installed (e.g, `14.11`)
  - `14.XX.YYYYY` for a specific full version number (e.g, `14.11.25503`)
- `uwp` – set `true` to build for Universal Windows Platform (i.e., for Windows Store)
- `spectre` – set `true` to use Visual Studio libraries with [Spectre](https://meltdownattack.com) mitigations

## Caveats

### Name conflicts with `shell: bash`

Using `shell: bash` in Actions may shadow some of the paths added by MSVC.
In particular, `link.exe` (Microsoft C linker) is prone to be shadowed by `/usr/bin/link` (GNU filesystem link tool).

Unfortunately, this happens because GitHub Actions unconditionally *prepend* GNU paths when `shell: bash` is used,
on top of any paths set by `msvc-dev-cmd`, every time at the start of each new step.
Hence, there aren't many non-destructive options here.

If you experience compilation errors where `link` complains about unreasonable command-line arguments,
“extra operand *something-something*” – that's probably it.
Recommended workaround is to remove `/usr/bin/link` if that interferes with your builds.
If this is not acceptable, please file an issue, then we'll figure out something better.

### Reconfiguration

You can invoke `ilammy/msvc-dev-cmd` multiple times during your jobs with different inputs
to reconfigure the environment for building with different settings
(e.g., to target multiple architectures).

```yaml
jobs:
  release:
    steps:
      # ...
      - name: Configure build for amd64
        uses: ilammy/msvc-dev-cmd@v1
        with:
          arch: amd64

      - run: build # (for amd64)

      - name: Configure build for x86
        uses: ilammy/msvc-dev-cmd@v1
        with:
          arch: amd64_x86

      - run: build # (for x86)

      - name: Configure build for ARM64
        uses: ilammy/msvc-dev-cmd@v1
        with:
          arch: amd64_arm64

      - run: build # (for ARM64)

      # ...
```

This mostly works but it's not really recommended
since Developer Command Prompt was not meant for recursive reconfiguration.
That said, if it does not work for you, please file an issue.

Consider using [`strategy.matrix`](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idstrategymatrix)
to execute different build configuration in parallel, independent environments.

## License

MIT, see [LICENSE](LICENSE).
