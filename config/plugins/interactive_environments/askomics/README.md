# AskOmics Interactive Environment
Galaxy Interactive environment files for AskOmics


## Set up the interactive environment

- Clone this repository into your Galaxy instance

        git clone https://github.com/xgaia/askomics-interactive-environment.git ${GALAXY_DIRECTORY}/config/plugins/interactive_environments/askomics

- Copy configuration file

        cp ${GALAXY_DIRECTORY}/config/plugins/interactive_environments/askomics/config/askomics.ini.sample ${GALAXY_DIRECTORY}/config/plugins/interactive_environments/askomics/config/askomics.ini

Uncomment line `galaxy_url =` and add your local galaxy url

- Update `galaxy.ini` with the following properties

        [filter:proxy-prefix]
        use = egg:PasteDeploy#prefix
        prefix = /galaxy
        interactive_environment_plugins_directory = config/plugins/interactive_environments/
        dynamic_proxy_manage=True
        dynamic_proxy=node
        dynamic_proxy_session_map=database/session_map.sqlite
        dynamic_proxy_bind_port=8800
        dynamic_proxy_bind_ip=0.0.0.0
        dynamic_proxy_debug=True
        dynamic_proxy_external_proxy=True
        dynamic_proxy_prefix=gie_proxy

- If you are using a nginx webserver, add this lines into it


        # Global GIE configuration
        location /gie_proxy {
            proxy_pass http://${LOCAL_IP}:8800/gie_proxy;
            proxy_redirect off;
        }

        location /gie_proxy/askomics/ {
            proxy_pass http://${LOCAL_IP}:8800/;
            proxy_redirect http://${LOCAL_IP}:8800 ${SERVER_URL}/gie_proxy/askomics/;
        }

- Pull the docker image

        docker pull xgaia/askomics-ie
