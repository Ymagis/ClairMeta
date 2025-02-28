set -ex

sudo apt-get -y update

##
# Install asdcplib

sudo apt-get -y install libssl-dev libxerces-c-dev libexpat-dev

BASE_DIR=`pwd`
WORK_DIR=`mktemp -d`
cd "$WORK_DIR"

git clone https://github.com/cinecert/asdcplib.git && cd asdcplib
git checkout rel_2_13_0
mkdir build && cd build

cmake ..
sudo cmake --build . --target install --config Release -- -j$(nproc)

cd "$BASE_DIR"
rm -rf "$WORK_DIR"


##
# ClairMeta dependencies

sudo apt-get -y install mediainfo sox
