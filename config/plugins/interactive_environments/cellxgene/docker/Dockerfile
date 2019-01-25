FROM ubuntu:bionic

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

RUN apt-get update && \
    apt-get install -y build-essential libxml2-dev python3-dev python3-pip zlib1g-dev

RUN pip3 install cellxgene

ADD ./run_cellxgene.sh /

ENTRYPOINT ["/run_cellxgene.sh"]

EXPOSE 80
