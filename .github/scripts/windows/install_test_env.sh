set -ex

##
# Install asdcplib

export CMAKE_PREFIX_PATH="$VCPKG_INSTALLATION_ROOT/installed/x64-windows"
vcpkg install openssl:x64-windows
vcpkg install xerces-c:x64-windows

BASE_DIR=`pwd`
WORK_DIR=`mktemp -d`
cd "$WORK_DIR"

git clone https://github.com/cinecert/asdcplib.git && cd asdcplib
git checkout rel_2_13_0
mkdir build && cd build

cmake \
    -DCMAKE_INSTALL_PREFIX=$VCPKG_INSTALLATION_ROOT/installed/x64-windows \
    -DOpenSSLLib_PATH=$VCPKG_INSTALLATION_ROOT/installed/x64-windows/lib/libcrypto.lib \
    -DOpenSSLLib_include_DIR=$VCPKG_INSTALLATION_ROOT/installed/x64-windows/include \
    -DXercescppLib_PATH=$VCPKG_INSTALLATION_ROOT/installed/x64-windows/lib/xerces-c_3.lib \
    -DXercescppLib_Debug_PATH=$VCPKG_INSTALLATION_ROOT/installed/x64-windows/lib/xerces-c_3.lib \
    -DXercescppLib_include_DIR=$VCPKG_INSTALLATION_ROOT/installed/x64-windows/include \
    ..
cmake --build . --target install --config Release

cd "$BASE_DIR"
rm -rf "$WORK_DIR"


##
# ClairMeta other dependencies
choco install mediainfo-cli

ls -lR $VCPKG_INSTALLATION_ROOT/installed/x64-windows
