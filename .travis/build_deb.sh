#!/bin/bash

set -x

mkdir /deb
cd /tmp

# Cinecert asdcplib packaging
wget --no-check-certificate -P /tmp \
  http://download.cinecert.com/asdcplib/asdcplib-2.9.30.tar.gz
tar xzf /tmp/asdcplib-2.9.30.tar.gz
cd asdcplib-2.9.30
cp -r /build_src/debian-asdcplib debian/
sed -i "s/UNSTABLE/$DISTRIBUTION/g" debian/changelog
dpkg-buildpackage -us -uc
mv ../asdcplib*.deb /deb
cd -

# Setup virtualenv
pip3 install pipenv

# We manually download clairmeta source distribution and add a stdeb.cfg file
# corresponding to the current python version build.
pipenv run pip3 download --no-binary :all: --no-deps clairmeta
mkdir clairmeta && tar xzf clairmeta-*.tar.gz -C clairmeta --strip-components=1
cp /build_src/stdeb-python3.cfg clairmeta/stdeb.cfg
tar czf clairmeta.tar.gz clairmeta

# We use py2deb to automatically create debian packages from PyPI packages,
# requirements are also packaged. Some specific topic to watch :
# 1/ Rename python-magic to avoid name conflict with already existing
#    debian package.
# 2/ py2deb force a downgrade of pip to 7.1.2 (seems to be a pip-accel
#    requirement, see https://github.com/paylogic/pip-accel/issues/73).
#    This means newest pip functionalities like environment markers are not
#    supported, cryptography package use one for cffi depends. We need to add
#    manually somewhere in the depends chain, currently directly to clairmeta
#    package (see https://github.com/pyca/cryptography/issues/4001).
#    The same kind of issue occurs for cryptography python 2 specific depends
#    enum34 and ipaddress that are handled with environment markers.
pipenv run pip3 install py2deb
pipenv run py2deb -r /deb --name-prefix=python3 --rename=python-magic,python3-magic-ahupp -y -- clairmeta.tar.gz
pipenv run py2deb -r /deb --name-prefix=python3 -y -- cffi>=1.7

# Bintray packages deployment
for DEB in /deb/*.deb
do
  /build_src/bintray.sh $DEB
done