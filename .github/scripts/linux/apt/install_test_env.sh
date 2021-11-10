set -ex

# install keys
sudo apt-get update
sudo apt-get -y install dirmngr curl
# key for bintray
gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv 379CE192D401AB61
gpg --export --armor 379CE192D401AB61 | sudo apt-key add -

# add apt list
source /etc/lsb-release
echo "deb https://dl.bintray.com/ymagis/Clairmeta ${DISTRIB_CODENAME} main" | sudo tee /etc/apt/sources.list.d/clairmeta.list

# TODO: should we just pull asdcplib and compile here ?

# clairmeta dependencies
sudo apt-get update
sudo apt-get -y install asdcplib mediainfo sox