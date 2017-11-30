FROM ubuntu:artful

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    dput \
    curl \
    wget \
    libxml2-dev \
    build-essential \
    devscripts \
    fakeroot \
    make \
    gcc \
    locales \
    debhelper \
    python \
    python-dev \
    python-pip \
    python-all \
    python-setuptools \
    python-all-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-all \
    python3-setuptools \
    python3-all-dev

RUN dpkg-reconfigure locales && \
    locale-gen en_US.UTF-8 && \
    /usr/sbin/update-locale LANG=en_US.UTF-8

RUN apt-get update && apt-get install -y \
    apt-transport-https \
    libffi-dev \
    autotools-dev \
    libssl-dev \
    lintian

RUN pip3 install -U pip setuptools

ENV LC_ALL en_US.UTF-8

CMD cd /build_src && ./build_deb.sh