# Have not yet gotten this to work - goal was to launch the prox in a Docker container.
# Networking is a bit tricky though - could not get the child proxy to talk to the child
# Jupyter container.


# sudo docker build --no-cache=true -t gxproxy .
# sudo docker run --net host -v /home/john/workspace/galaxy-central/database:/var/gxproxy -p 8800:8800 -t gxproxy lib/main.js --sessions /var/gxproxy/session_map.json --ip 0.0.0.0 --port 8800

FROM node:0.11.13

RUN mkdir -p /usr/src/gxproxy
WORKDIR /usr/src/gxproxy

ADD package.json /usr/src/gxproxy/
RUN npm install
ADD . /usr/src/gxproxy

CMD [ "lib/main.js" ]
