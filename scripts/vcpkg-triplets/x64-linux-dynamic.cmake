set(VCPKG_TARGET_ARCHITECTURE x64)
set(VCPKG_CRT_LINKAGE dynamic)
set(VCPKG_LIBRARY_LINKAGE dynamic)

set(VCPKG_CMAKE_SYSTEM_NAME Linux)

set(VCPKG_FIXUP_ELF_RPATH ON)

# Stop curl from loading the host's /etc/ssl/openssl.cnf into the vendored
# OpenSSL at init time -- an incompatible host config can break TLS entirely
# (pycurl#1066). Forwarded to curl's CMake build via vcpkg_cmake_configure.
set(VCPKG_CMAKE_CONFIGURE_OPTIONS "-DCURL_DISABLE_OPENSSL_AUTO_LOAD_CONFIG=ON")
