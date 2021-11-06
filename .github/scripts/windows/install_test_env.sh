set -ex

##
# Install asdcplib

# env
# ls "C:\ProgramData\chocolatey"
# ls "C:\vcpkg"
# ls "C:\Program Files (x86)"
# ls "C:\Program Files"
# ls -R "C:\Program Files\OpenSSL"

# vcpkg install xerces-c openssl

BASE_DIR=`pwd`
WORK_DIR=`mktemp -d`
cd "$WORK_DIR"

git clone https://github.com/openssl/openssl.git && cd openssl
git checkout OpenSSL_1_1_1j
perl Configure VC-WIN64A
nmake
nmake install
cd "$BASE_DIR"

ls "C:\Program Files\Common Files\SSL"

git clone https://github.com/cinecert/asdcplib.git && cd asdcplib
git checkout rel_2_10_35
mkdir build && cd build

# Hombrew OpenSSL is keg-only, need to help asdcplib's find_library
cmake \
    -DCMAKE_TOOLCHAIN_FILE="libcrypto-1_1-x64.dll" \
    ..
cmake --build . --target install --config Release

# cd "$BASE_DIR"
# rm -rf "$WORK_DIR"


##
# ClairMeta other dependencies
# vcpkg install libmediainfo
choco install mediainfo sox.portable

mediainfo --version
