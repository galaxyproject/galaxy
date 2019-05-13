FROM python:3.6.8-slim
 
RUN pip3 install cellxgene scanpy==1.4 && rm -rf ~/.cache

ADD ./run_cellxgene.sh /

##ENTRYPOINT ["/run_cellxgene.sh"]

EXPOSE 80
