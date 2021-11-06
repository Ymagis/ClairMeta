#!/bin/bash

# End support for ubuntu trusty, the ppa we used to have a python 3.6
# install is no longer working as of June 2020
# docker build -f .travis/Dockerfile-build-trusty -t clairmeta/build_trusty .
# docker run -it \
#   -v $PWD/.travis:/build_src \
#   -e "BINTRAY_USER=${BINTRAY_USER}" \
#   -e "BINTRAY_ORG=${BINTRAY_ORG}" \
#   -e "BINTRAY_REPO=${BINTRAY_REPO}" \
#   -e "BINTRAY_TOKEN=${BINTRAY_TOKEN}" \
#   -e "DISTRIBUTION=trusty" \
#   clairmeta/build_trusty

docker build -f .travis/Dockerfile-build-xenial -t clairmeta/build_xenial .
docker run -it \
  -v $PWD/.travis:/build_src \
  -e "BINTRAY_USER=${BINTRAY_USER}" \
  -e "BINTRAY_ORG=${BINTRAY_ORG}" \
  -e "BINTRAY_REPO=${BINTRAY_REPO}" \
  -e "BINTRAY_TOKEN=${BINTRAY_TOKEN}" \
  -e "DISTRIBUTION=xenial" \
  clairmeta/build_xenial

docker build -f .travis/Dockerfile-build-artful -t clairmeta/build_artful .
docker run -it \
  -v $PWD/.travis:/build_src \
  -e "BINTRAY_USER=${BINTRAY_USER}" \
  -e "BINTRAY_ORG=${BINTRAY_ORG}" \
  -e "BINTRAY_REPO=${BINTRAY_REPO}" \
  -e "BINTRAY_TOKEN=${BINTRAY_TOKEN}" \
  -e "DISTRIBUTION=artful" \
clairmeta/build_artful

docker build -f .travis/Dockerfile-build-bionic -t clairmeta/build_bionic .
docker run -it \
  -v $PWD/.travis:/build_src \
  -e "BINTRAY_USER=${BINTRAY_USER}" \
  -e "BINTRAY_ORG=${BINTRAY_ORG}" \
  -e "BINTRAY_REPO=${BINTRAY_REPO}" \
  -e "BINTRAY_TOKEN=${BINTRAY_TOKEN}" \
  -e "DISTRIBUTION=bionic" \
  clairmeta/build_bionic
