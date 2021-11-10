#!/bin/bash

docker build -f .travis/Dockerfile-install-trusty -t clairmeta/install_trusty .
docker run -it -v $PWD/tests/resources/DCP/ECL-SET:/dcp  clairmeta/install_trusty

docker build -f .travis/Dockerfile-install-xenial -t clairmeta/install_xenial .
docker run -it -v $PWD/tests/resources/DCP/ECL-SET:/dcp  clairmeta/install_xenial

docker build -f .travis/Dockerfile-install-bionic -t clairmeta/install_bionic .
docker run -it -v $PWD/tests/resources/DCP/ECL-SET:/dcp  clairmeta/install_bionic