#!/bin/bash

set -x

API=https://api.bintray.com
PACKAGE_DESCRIPTOR=bintray-package.json

BINTRAY_USER=$1
BINTRAY_ORG=$2
BINTRAY_API_KEY=$3
BINTRAY_REPO=$4
DEB=$5
DISTRIB=$6

PCK_NAME=$(dpkg-deb -f ${DEB} Package)
PCK_VERSION=$(dpkg-deb -f ${DEB} Version)+${DISTRIB}
PCK_DESC=$(dpkg-deb -f ${DEB} Description)
FILE_TARGET_PATH=$(basename $DEB)

main() {
  echo ${DEB}
  CURL="curl -u${BINTRAY_USER}:${BINTRAY_API_KEY} -H Content-Type:application/json -H Accept:application/json"
  if (check_package_exists); then
    echo "The package ${PCK_NAME} does not exit. It will be created"
    create_package
  fi

  deploy_deb
}

check_package_exists() {
  echo "Checking if package ${PCK_NAME} exists..."
  package_exists=`[ $(${CURL} --write-out %{http_code} --silent --output /dev/null -X GET  ${API}/packages/${BINTRAY_ORG}/${BINTRAY_REPO}/${PCK_NAME})  -eq 200 ]`
  echo "Package ${PCK_NAME} exists? y:1/N:0 ${package_exists}"
  return ${package_exists}
}

create_package() {
  echo "Creating package ${PCK_NAME}..."
  if [ -f "${PACKAGE_DESCRIPTOR}" ]; then
    data="@${PACKAGE_DESCRIPTOR}"
  else
    data="{
    \"name\": \"${PCK_NAME}\",
    \"desc\": \"auto\",
    \"desc_url\": \"auto\",
    \"labels\": [\"python3\"],
    \"licenses\": [\"BSD 3-Clause\"],
    \"vcs_url\": \"https://github.com/Ymagis/ClairMeta\"
    }"
  fi

  ${CURL} -X POST -d "${data}" ${API}/packages/${BINTRAY_ORG}/${BINTRAY_REPO}
}

deploy_deb() {
  if (upload_content); then
    echo "Publishing ${DEB}..."
    ${CURL} -X POST ${API}/content/${BINTRAY_ORG}/${BINTRAY_REPO}/${PCK_NAME}/${PCK_VERSION}/publish -d "{ \"discard\": \"false\" }"
  else
    echo "[SEVERE] First you should upload your deb ${DEB}"
  fi
}

upload_content() {
  echo "Uploading ${DEB}..."
  uploaded=`[ $(${CURL} --write-out %{http_code} --silent -T ${DEB} "${API}/content/${BINTRAY_ORG}/${BINTRAY_REPO}/${PCK_NAME}/${PCK_VERSION}/pool/main/${DISTRIB}/${PCK_NAME}/${FILE_TARGET_PATH};deb_distribution=${DISTRIB};deb_component=main;deb_architecture=i386,amd64") -eq 201 ]`
  echo "DEB ${DEB} uploaded? y:1/N:0 ${uploaded}"
  return ${uploaded}
}

main "$@"