"""

"""

from kubernetes import client, config
from kubernetes.client.rest import ApiException

DEPLOYMENT_NAME = "rabbitmq-deployment"
RABBITMQ_NAME = "rabbitmq"
RABBITMQ_MT_NAME = "rabbitmq-management"
APP_TAG = "rabbitmq"

class RabbitMQK8s(object):
    def __init__(self):
        # Configs can be set in Configuration class directly or using helper
        # utility. If no argument provided, the config will be loaded from
        # default location.
        config.load_kube_config()
        self.api_instance = client.CoreV1Api()
        self.namespace = "default"

    def __create_service(self, namespace, manifest):
        try:
            api_response = self.api_instance.create_namespaced_service(namespace, manifest)
        except ApiException as e:
            print("Exception when calling CoreV1Api->create_namespaced_endpoints: %s\n" % e)
        return api_response

    def __create_statefulset(self, namespace, manifest):
        try:
            # create an instance of the API class
            api_instance = client.AppsV1beta1Api()
            api_response = api_instance.create_namespaced_stateful_set(namespace, manifest)
        except ApiException as e:
            print("Exception when calling AppsV1beta1Api->create_namespaced_stateful_set: %s\n" % e)
        return api_response

    def create_rabbitmq(self):
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": RABBITMQ_NAME,
                "labels": {
                    "app": APP_TAG
                }
            },
            "spec": {
                "ports": [
                    {
                        "name": "amqp",
                        "port": 5672
                    },
                    {
                        "name": "epmd",
                        "port": 4369
                    },
                    {
                        "name": "rabbitmq-dist",
                        "port": 25672
                    }
                ],
                "clusterIP": "None",
                "selector": {
                    "app": APP_TAG
                }
            }
        }
        return self.__create_service(self.namespace, manifest)

    def create_rabbitmq_management(self):
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": RABBITMQ_MT_NAME,
                "labels": {
                    "app": APP_TAG
                }
            },
            "spec": {
                "ports": [
                    {
                        "name": "http",
                        "port": 15672
                    }
                ],
                "selector": {
                    "app": APP_TAG
                },
                "type": "NodePort"
            }
        }
        return self.__create_service(self.namespace, manifest)

    def create_rabbitmq_statefulset(self):
        manifest = {
            # TODO
        }
        return self.__create_statefulset(self.namespace, manifest)

    def create_deployment(self):
        # TODO: authorization and cookies.
        # Configure API key authorization: BearerToken
        # configuration = client.Configuration()
        # configuration.api_key['authorization'] = 'YOUR_API_KEY'
        # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
        # configuration.api_key_prefix['authorization'] = 'Bearer'
        self.create_rabbitmq()
        self.create_rabbitmq_management()
        self.create_rabbitmq_statefulset()

    def update_deployment(self, api_instance, deployment):
        pass

    def delete_deployment(self, api_instance):
        pass
