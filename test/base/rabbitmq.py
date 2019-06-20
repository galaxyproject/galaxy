"""

"""
import time
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

# Some kubernetes objects (e.g., Statefulset) are slow-to-delete.
# Hence, sleep for few seconds after an object delete request is
# sent to the cluster. The sleep time is tentative based on experiments
# on a local machine.
# An alternative (or maybe a complementary) method to sleeping is to
# query kubernetes for the object being deleted, and check if it exists
# after the delete request is submitted to the cluster.
DELETE_SLEEP_TIME = 5


class RabbitMQK8s(object):
    def __init__(self):
        # Configs can be set in Configuration class directly or using helper
        # utility. If no argument provided, the config will be loaded from
        # default location.
        config.load_kube_config()
        self.core_api = client.CoreV1Api()
        self.apps_api = client.AppsV1beta1Api()
        self.namespace = "default"

    def __create_object(self, create_method, delete_method, list_method, manifest, retries=MAX_RETRIES):
        try:
            return create_method(self.namespace, manifest)
        except ApiException as e:
            if "object is being deleted" in e.body:
                # This case can happen if kubernetes has not completed object deletion
                # yet; it can mostly happen with Statefulset as it is a slow-to-delete
                # object.
                time.sleep(DELETE_SLEEP_TIME)
            if (e.reason == "Conflict" or e.status == 409) and retries > 1:
                # Do not try recalling API if it fails deleting the service.
                try:
                    self.__delete_object(delete_method, list_method, manifest["metadata"]["name"])
                except ApiException:
                    raise ApiException
                else:
                    return self.__create_object(create_method, delete_method, list_method, manifest, retries=retries-1)
            print("Exception when calling the method {0}; error: {1}\n".format(create_method, e))

    def __delete_object(self, delete_method, list_method, name):
        try:
            api_response = delete_method(
                name=name,
                namespace=self.namespace,
                grace_period_seconds=0,
                async_req=False
            )
            for item in list_method(self.namespace).items:
                if item.metadata.name == name:
                    time.sleep(DELETE_SLEEP_TIME)
            for item in list_method(self.namespace).items:
                if item.metadata.name == name:
                    raise ApiException(reason="Object `{}` is still not deleted having waited for {} seconds "
                                              "after delete request was sent.".format(name, DELETE_SLEEP_TIME))
            return api_response
        except ApiException as e:
            # Note, there is a corner case with an exception with 404 status;
            # this case can happen (usually with Statefulset objects) when
            # an object was requested to be deleted, and was not deleted by
            # the time when its availability was check, hence another delete
            # request was sent, but by then the object got deleted (i.e.,
            # between the time its availability was checked and a new delete
            # request was made). Hence, be cautious when dealing with 404
            # errors. A possible solution can be to increase DELETE_SLEEP_TIME.
            print("Exception when calling the method {0}; error: {1}\n".format(delete_method, e))
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
                # Determines which set of pods are targeted by this service.
                "selector": {
                    "app": APP_TAG
                }
            }
        }
        api_response = self.__create_object(
            self.core_api.create_namespaced_service,
            self.core_api.delete_namespaced_service,
            self.core_api.list_namespaced_service,
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
                # Determines which set of pods are targeted by this service.
                "selector": {
                    "app": APP_TAG
                },
                "type": "NodePort"
            }
        }
        api_response = self.__create_object(
            self.core_api.create_namespaced_service,
            self.core_api.delete_namespaced_service,
            self.core_api.list_namespaced_service,
            manifest)
        return api_response

    def create_rabbitmq_stateful_set(self):
        # TODO: a post script that (1) stops rabbits, (2) restarts
        # the cluster, (3) joins the rabbits to the cluster.
        manifest = {
            "apiVersion": "apps/v1beta1",
            "kind": "StatefulSet",
            "metadata": {
                "name": RABBITMQ_NAME,
                "labels": {
                    "app": APP_TAG
                }
            },
            "spec": {
                "serviceName": RABBITMQ_MT_NAME,
                "replicas": 5,
                "template": {
                    "metadata": {
                        "name": RABBITMQ_NAME,
                        "labels": {
                            "app": APP_TAG
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": "rabbitmq",
                                "image": "rabbitmq:3.6.6-management-alpine",
                                "env": [
                                    {
                                        "name": "RABBITMQ_ERLANG_COOKIE",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "name": "rabbitmq-config",
                                                "key": "erlang-cookie"
                                            }
                                        }
                                    }
                                ],
                                "ports": [
                                    {
                                        "name": "amqp",
                                        "containerPort": 5672
                                    }
                                ],
                                "volumeMounts": [
                                    {
                                        "name": "rabbitmq",
                                        "mountPath": "/var/lib/rabbitmq"
                                    }
                                ]
                            }
                        ]
                    }
                },
                "volumeClaimTemplates": [
                    {
                        "metadata": {
                            "name": "rabbitmq",
                            "annotations": {
                                "volume.alpha.kubernetes.io/storage-class": "anything"
                            }
                        },
                        "spec": {
                            "accessModes": [
                                "ReadWriteOnce"
                            ],
                            "resources": {
                                "requests": {
                                    "storage": "1Gi"
                                }
                            }
                        }
                    }
                ]
            }
        }
        api_response = self.__create_object(
            self.apps_api.create_namespaced_stateful_set,
            self.apps_api.delete_namespaced_stateful_set,
            self.apps_api.list_namespaced_stateful_set,
            manifest)
        return api_response

    def create_deployment(self):
        # TODO: authorization and cookies.
        # Configure API key authorization: BearerToken
        # configuration = client.Configuration()
        # configuration.api_key['authorization'] = 'YOUR_API_KEY'
        # Uncomment below to setup prefix (e.g. Bearer) for API key, if needed
        # configuration.api_key_prefix['authorization'] = 'Bearer'

        # Note: the following commands define
        # two kubernetes services for rabbitmq (rabbitmq
        # and its management).
        # - the rabbitmq service is defined "headless", and reachable only from within the cluster
        # - the management rabbitmq service is defined

        self.create_rabbitmq_management()

        # The required headless service for StatefulSets
        self.create_rabbitmq()

        self.create_rabbitmq_stateful_set()

    def update_deployment(self, api_instance, deployment):
        pass

    def delete_deployment(self, name):
        pass

    def delete_service(self, name):
        return self.__delete_object(self.core_api.delete_namespaced_service, name)
