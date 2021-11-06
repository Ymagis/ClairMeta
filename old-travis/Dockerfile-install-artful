FROM ubuntu:artful

RUN apt-get update && apt-get install -y apt-transport-https dirmngr

RUN gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv 379CE192D401AB61 \
 && gpg --export --armor 379CE192D401AB61 | apt-key add - \
 && echo "deb https://dl.bintray.com/ymagis/Clairmeta artful main" | tee /etc/apt/sources.list.d/clairmeta.list

RUN apt-get update \
 && apt-get install -y python3-clairmeta

ENV DCP="/dcp/ECL01-SINGLE-CPL_TST_S_EN-XX_UK-U_71_2K_DI_20171218_ECL_IOP_OV/"

CMD python3.6 -m clairmeta.cli check -type dcp ${DCP}