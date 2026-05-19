#!/bin/bash
# Sets up mono and NuGet credentials for vcpkg binary caching via GitHub Packages.
# No-ops when VCPKG_BINARY_SOURCES or GITHUB_TOKEN are unset (e.g. aarch64, local builds).
set -e

if [ -z "$VCPKG_BINARY_SOURCES" ] || [ -z "$GITHUB_TOKEN" ]; then
    exit 0
fi

nuget="$(env -u VCPKG_FORCE_SYSTEM_BINARIES vcpkg fetch nuget | tail -n 1)"
mono "${nuget}" \
    sources add \
    -source "https://nuget.pkg.github.com/${GITHUB_REPOSITORY_OWNER}/index.json" \
    -storepasswordincleartext \
    -name "GitHub" \
    -username "${GITHUB_REPOSITORY_OWNER}" \
    -password "${GITHUB_TOKEN}"
mono "${nuget}" \
    setapikey "${GITHUB_TOKEN}" \
    -source "https://nuget.pkg.github.com/${GITHUB_REPOSITORY_OWNER}/index.json"

ln -s "${nuget}" /usr/local/bin/nuget
