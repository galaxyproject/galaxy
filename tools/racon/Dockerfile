FROM nvidia/cuda:10.1-devel-ubuntu18.04

RUN apt-get -y update
RUN apt-get install -y make build-essential zlib1g-dev python git cmake

RUN mkdir /tmp/racon
WORKDIR /tmp/racon
RUN git clone --recursive https://github.com/clara-genomics/racon-gpu.git racon
WORKDIR /tmp/racon/racon
RUN mkdir build
WORKDIR /tmp/racon/racon/build
RUN cmake -DCMAKE_BUILD_TYPE=Release -Dracon_enable_cuda=ON ..
RUN make
RUN cp bin/racon /usr/bin/racon_gpu
RUN chmod a+x /usr/bin/racon_gpu

WORKDIR /tmp/racon/racon
RUN rm -rf build
RUN mkdir build
WORKDIR /tmp/racon/racon/build
RUN cmake -DCMAKE_BUILD_TYPE=Release -Dracon_enable_cuda=OFF ..
RUN make
RUN cp bin/racon /usr/bin/racon_cpu
RUN chmod a+x /usr/bin/racon_cpu
