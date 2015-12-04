FROM digitallyseamless/nodejs-bower-grunt
RUN mkdir /gx && \
    cd /gx && \
    wget https://github.com/galaxyproject/galaxy/archive/dev.tar.gz && \
    tar xvfz dev.tar.gz && \
    cd galaxy-dev/client && \
    npm install -g && \
    cd / && \
    rm -rf /gx

WORKDIR /data/client
ADD ./.docker-build.sh /build.sh
CMD ["/build.sh"]
