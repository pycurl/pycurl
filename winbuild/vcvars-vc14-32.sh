# Courtesy of libiconv 1.15

# Set environment variables for using MSVC 14,
# for creating native 32-bit Windows executables.

# Windows C library headers and libraries.
WindowsCrtIncludeDir='C:\Program Files (x86)\Windows Kits\10\Include\10.0.10240.0\ucrt'
WindowsCrtLibDir='C:\Program Files (x86)\Windows Kits\10\Lib\10.0.10240.0\ucrt\'
INCLUDE="${WindowsCrtIncludeDir};$INCLUDE"
LIB="${WindowsCrtLibDir}x86;$LIB"

# Windows API headers and libraries.
WindowsSdkIncludeDir='C:\Program Files (x86)\Windows Kits\8.1\Include\'
WindowsSdkLibDir='C:\Program Files (x86)\Windows Kits\8.1\Lib\winv6.3\um\'
INCLUDE="${WindowsSdkIncludeDir}um;${WindowsSdkIncludeDir}shared;$INCLUDE"
LIB="${WindowsSdkLibDir}x86;$LIB"

# Visual C++ tools, headers and libraries.
VSINSTALLDIR='C:\Program Files (x86)\Microsoft Visual Studio 14.0'
VCINSTALLDIR="${VSINSTALLDIR}"'\VC'
PATH=`cygpath -u "${VCINSTALLDIR}"`/bin:"$PATH"
INCLUDE="${VCINSTALLDIR}"'\include;'"${INCLUDE}"
LIB="${VCINSTALLDIR}"'\lib;'"${LIB}"

export INCLUDE LIB
