FROM python:3.6.8-slim

RUN apt-get update && apt-get install -y \
    net-tools \
 && rm -rf /var/lib/apt/lists/*
 
RUN pip3 install cellxgene galaxy-ie-helpers && rm -rf ~/.cache

ADD ./run_cellxgene.sh /

ENTRYPOINT ["/run_cellxgene.sh"]

EXPOSE 80
