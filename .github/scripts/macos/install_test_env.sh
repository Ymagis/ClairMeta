set -ex

brew update

##
# Install asdcplib

brew install openssl xerces-c

BASE_DIR=`pwd`
WORK_DIR=`mktemp -d`
cd "$WORK_DIR"

git clone https://github.com/cinecert/asdcplib.git && cd asdcplib
git checkout rel_2_13_0
mkdir build && cd build

cmake -DCMAKE_MACOSX_RPATH=ON ..
sudo cmake --build . --target install --config Release -- -j$(sysctl -n hw.ncpu)

cd "$BASE_DIR"
rm -rf "$WORK_DIR"


##
# ClairMeta other dependencies
brew install mediainfo sox
