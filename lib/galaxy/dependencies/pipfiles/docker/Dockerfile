FROM python:3.5

ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# Install Pipenv
RUN apt update && apt -y upgrade
RUN pip install pipenv

ADD docker_script.sh /docker_script.sh

WORKDIR /working

CMD bash /docker_script.sh
