"""

"""

from kubernetes import client, config
from kubernetes.client.rest import ApiException

DEPLOYMENT_NAME = "rabbitmq-deployment"
RABBITMQ_NAME = "rabbitmq"
RABBITMQ_MT_NAME = "rabbitmq-management"
APP_TAG = "rabbitmq"

# In case the service exists (conflict), this property sets for how
# many times it will attempt to create the service:
# deletes for MAX_RETRIES -1 times and creates for MAX_RETRIES times.
MAX_RETRIES = 3


class RabbitMQK8s(object):
    def __init__(self):
        # Configs can be set in Configuration class directly or using helper
        # utility. If no argument provided, the config will be loaded from
        # default location.
        config.load_kube_config()
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1beta1Api()
        self.namespace = "default"

    def __create_object(self, create_method, delete_method, namespace, manifest, retries=MAX_RETRIES):
        try:
            return create_method(namespace, manifest)
        except ApiException as e:
            if (e.reason == "Conflict" or e.status == 409) and retries > 1:
                # Do not try recalling API if it fails deleting the service.
                try:
                    self.__delete_object(delete_method, manifest["metadata"]["name"])
                except ApiException:
                    raise ApiException
                else:
                    return self.__call_api(create_method, namespace, manifest, retries=retries-1)
            print("Exception when calling the method {0}; error: {1}\n".format(create_method, e))

    def __delete_object(self, method, name):
        try:
            api_response = method(
                name=name,
                namespace=self.namespace,
                grace_period_seconds=0,
                async_req=False
            )
            return api_response
        except ApiException as e:
            print("Exception when calling CoreV1Api->delete_namespaced_service: %s\n" % e)
            raise

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
        api_response = self.__create_object(
            self.core_api.create_namespaced_service,
            self.core_api.delete_namespaced_service,
            self.namespace,
            manifest)
        return api_response

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
        api_response = self.__create_object(
            self.core_api.create_namespaced_service,
            self.core_api.delete_namespaced_service,
            self.namespace,
            manifest)
        return api_response

    def create_rabbitmq_stateful_set(self):
        manifest = {
            # TODO
        }
        api_response = self.__create_object(
            self.apps_api.create_namespaced_stateful_set,
            self.apps_api.delete_namespaced_stateful_set,
            self.namespace,
            manifest)
        return api_response

    def create_deployment(self):
        # TODO: authorization and cookies.
        # Configure API key authorization: BearerToken
        # configuration = client.Configuration()
        # configuration.api_key['authorization'] = 'YOUR_API_KEY'
        # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
        # configuration.api_key_prefix['authorization'] = 'Bearer'
        self.create_rabbitmq()
        self.create_rabbitmq_management()
        self.create_rabbitmq_stateful_set()

    def update_deployment(self, api_instance, deployment):
        pass

    def delete_deployment(self, name):
        pass

    def delete_service(self, name):
        return self.__delete_object(self.core_api.delete_namespaced_service, name)
