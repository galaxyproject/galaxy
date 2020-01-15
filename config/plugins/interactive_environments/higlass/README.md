# HiGlass Galaxy Interactive Environment

This defines the Galaxy interactive environment for [HiGlass](https://higlass.io).
It uses the docker container [msauria/higlass-ie](https://hub.docker.com/r/msauria/higlass-ie)
and is suitable for both local and public instances.

## Installation

To install, simply copy this repo into the `config/plugins/interactive_environments` folder of
your Galaxy path.

## Configuration

There are two key settings in config/higlass.ini.sample that are required to get this environment
running properly.

1. In order to communicate properly with Galaxy, the docker container needs
to know how to connect to the local host running it. This is platform-dependent and currently
needs to be manually set. There are three options, one for Linux, Mac, and Windows. Simply
uncomment the correct one and make sure the other two are commented out. In addition, make sure
that the specified port matches the one that Galaxy is listening to, specified in your
`config/galaxy.yml` file under the parameter 'http'.

2. For the client-side of Galaxy to be able to communicate with the docker container, it needs
to know the ip address and port that the dynamic proxy is using. The port specified in
`config/galaxy.yml` under the parameter 'dynamic_proxy_bind_port'. The ip depends on whether
Galaxy is being run as a local or public instance. For a local instance, the ip must match the
value of the parameter 'dynamic_proxy_bind_ip' in `config/galaxy.yml`. A public instance uses
the publicly-accessible ip.
