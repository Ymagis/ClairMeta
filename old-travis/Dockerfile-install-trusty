FROM ubuntu:trusty

RUN apt-get update && apt-get install -y apt-transport-https

RUN echo "deb https://dl.bintray.com/ymagis/Clairmeta trusty main" | sudo tee /etc/apt/sources.list.d/clairmeta.list \
 && apt-get update \
 && apt-get install -y --force-yes python3-clairmeta

ENV DCP="/dcp/ECL01-SINGLE-CPL_TST_S_EN-XX_UK-U_71_2K_DI_20171218_ECL_IOP_OV/"

CMD python3 -m clairmeta.cli check -type dcp ${DCP}