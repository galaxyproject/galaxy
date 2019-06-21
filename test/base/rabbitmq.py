"""

"""
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException

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
        self.rbac_api = client.RbacAuthorizationV1beta1Api()

        # Please mind the following rules when naming objects:
        # names must consist of lower case alphanumeric
        # characters, `-`, or `.`, and must start and
        # end with an alphanumeric character.
        self.namespace = "gxy-tests"
        self.app_tag = "rabbitmq"
        self.objects_name = {
            "ConfigMap": "rabbitmq-config",
            "Role": "endpoint-reader",
            "Service": "rabbitmq",
            "ServiceAccount": "rabbitmq",
            "StatefulSet": "rabbitmq"
        }

        # To avoid conflicting resources when this class is
        # instantiated multiple times by different tests, a
        # timestamp is appended to all the resources name.
        self.timestamp = int(time.time())
        self.app_tag = "{0}-{1}".format(self.app_tag, self.timestamp)
        for name in self.objects_name:
            self.objects_name[name] = "{0}-{1}".format(
                self.objects_name[name],
                self.timestamp)

    def __create_namespace(self):
        """
        Will create a namespace with title self.namespace
        if a namespace with that title does not already exist.
        """
        namespaces = self.core_api.list_namespace()
        for namespace in namespaces.items:
            if self.namespace in namespace.metadata.self_link:
                return
        self.core_api.create_namespace(
            client.V1Namespace(
                metadata=client.V1ObjectMeta(
                    name=self.namespace)))

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

    def __create_service_account(self):
        manifest = {
            "kind": "ServiceAccount",
            "apiVersion": "v1",
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["ServiceAccount"]
            }
        }

        api_response = self.__create_object(
            self.core_api.create_namespaced_service_account,
            self.core_api.delete_namespaced_service_account,
            self.core_api.list_namespaced_service_account,
            manifest)
        return api_response

    def __create_role(self):
        manifest = {
            "kind": "Role",
            "apiVersion": "rbac.authorization.k8s.io/v1beta1",
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["Role"]
            },
            "rules": [
                {
                    "apiGroups": [
                        ""
                    ],
                    "verbs": [
                        "get"
                    ],
                    "resources": [
                        "endpoints"
                    ]
                }
            ]
        }

        api_response = self.__create_object(
            self.rbac_api.create_namespaced_role,
            self.rbac_api.delete_namespaced_role,
            self.rbac_api.list_namespaced_role,
            manifest)
        return api_response

    def __create_role_binding(self):
        manifest = {
            "kind": "RoleBinding",
            "apiVersion": "rbac.authorization.k8s.io/v1beta1",
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["Role"]
            },
            "subjects": [
                {
                    "kind": "ServiceAccount",
                    "name": self.objects_name["ServiceAccount"]
                }
            ],
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": "Role",
                "name": self.objects_name["Role"]
            }
        }

        api_response = self.__create_object(
            self.rbac_api.create_namespaced_role_binding,
            self.rbac_api.delete_namespaced_role_binding,
            self.rbac_api.list_namespaced_role_binding,
            manifest)
        return api_response

    def __create_service(self):
        manifest = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["Service"],
                "labels": {
                    "app": self.app_tag,
                    "type": "LoadBalancer"
                }
            },
            "spec": {
                "type": "NodePort",
                "ports": [
                    {
                        "port": 15672,
                        "protocol": "TCP",
                        "targetPort": 15672,
                        "name": "http",
                        "nodePort": 31672
                    },
                    {
                        "port": 5672,
                        "protocol": "TCP",
                        "targetPort": 5672,
                        "name": "amqp",
                        "nodePort": 30672
                    }
                ],
                "selector": {
                    "app": self.app_tag
                }
            }
        }

        api_response = self.__create_object(
            self.core_api.create_namespaced_service,
            self.core_api.delete_namespaced_service,
            self.core_api.list_namespaced_service,
            manifest)
        return api_response

    def __create_config_map(self):
        manifest = {
            "kind": "ConfigMap",
            "apiVersion": "v1",
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["ConfigMap"]
            },
            "data": {
                "enabled_plugins": "[rabbitmq_management,rabbitmq_peer_discovery_k8s].\n",
                "rabbitmq.conf": "## Cluster formation. See https://www.rabbitmq.com/cluster-formation.html to learn more.\ncluster_formation.peer_discovery_backend  = rabbit_peer_discovery_k8s\ncluster_formation.k8s.host = kubernetes.default.svc.cluster.local\n## Should RabbitMQ node name be computed from the pod's hostname or IP address?\n## IP addresses are not stable, so using [stable] hostnames is recommended when possible.\n## Set to \"hostname\" to use pod hostnames.\n## When this value is changed, so should the variable used to set the RABBITMQ_NODENAME\n## environment variable.\ncluster_formation.k8s.address_type = ip\n## How often should node cleanup checks run?\ncluster_formation.node_cleanup.interval = 30\n## Set to false if automatic removal of unknown/absent nodes\n## is desired. This can be dangerous, see\n##  * https://www.rabbitmq.com/cluster-formation.html#node-health-checks-and-cleanup\n##  * https://groups.google.com/forum/#!msg/rabbitmq-users/wuOfzEywHXo/k8z_HWIkBgAJ\ncluster_formation.node_cleanup.only_log_warning = true\ncluster_partition_handling = autoheal\n## See https://www.rabbitmq.com/ha.html#master-migration-data-locality\nqueue_master_locator=min-masters\n## See https://www.rabbitmq.com/access-control.html#loopback-users\nloopback_users.guest = false"
            }
        }

        api_response = self.__create_object(
            self.core_api.create_namespaced_config_map,
            self.core_api.delete_namespaced_config_map,
            self.core_api.list_namespaced_config_map,
            manifest)
        return api_response

    def __create_statefulset(self, replicas):
        manifest = {
            "kind": "StatefulSet",
            "apiVersion": "apps/v1beta1",
            "replicas": replicas,
            "metadata": {
                "namespace": self.namespace,
                "name": self.objects_name["StatefulSet"]
            },
            "spec": {
                "serviceName": self.objects_name["Service"],
                "template": {
                    "metadata": {
                        "labels": {
                            "app": self.app_tag
                        }
                    },
                    "spec": {
                        "terminationGracePeriodSeconds": 10,
                        "containers": [
                            {
                                "livenessProbe": {
                                    "initialDelaySeconds": 60,
                                    "exec": {
                                        "command": [
                                            "rabbitmqctl",
                                            "status"
                                        ]
                                    },
                                    "timeoutSeconds": 15,
                                    "periodSeconds": 60
                                },
                                "name": "rabbitmq-k8s",
                                "image": "rabbitmq:3.7",
                                "volumeMounts": [
                                    {
                                        "mountPath": "/etc/rabbitmq",
                                        "name": "config-volume"
                                    }
                                ],
                                "env": [
                                    {
                                        "valueFrom": {
                                            "fieldRef": {
                                                "fieldPath": "status.podIP"
                                            }
                                        },
                                        "name": "GXY_TEST_POD_IP"
                                    },
                                    {
                                        "name": "RABBITMQ_USE_LONGNAME",
                                        "value": "true"
                                    },
                                    {
                                        "name": "RABBITMQ_NODENAME",
                                        "value": "rabbit@$(GXY_TEST_POD_IP)"
                                    },
                                    {
                                        "name": "K8S_SERVICE_NAME",
                                        "value": self.objects_name["Service"]
                                    },
                                    {
                                        "name": "RABBITMQ_ERLANG_COOKIE",
                                        "value": "gxycookie"
                                    }
                                ],
                                "imagePullPolicy": "Always",
                                "readinessProbe": {
                                    "initialDelaySeconds": 20,
                                    "exec": {
                                        "command": [
                                            "rabbitmqctl",
                                            "status"
                                        ]
                                    },
                                    "timeoutSeconds": 10,
                                    "periodSeconds": 60
                                },
                                "ports": [
                                    {
                                        "protocol": "TCP",
                                        "name": "http",
                                        "containerPort": 15672
                                    },
                                    {
                                        "protocol": "TCP",
                                        "name": "amqp",
                                        "containerPort": 5672
                                    }
                                ]
                            }
                        ],
                        "serviceAccountName": self.objects_name["ServiceAccount"],
                        "volumes": [
                            {
                                "configMap": {
                                    "items": [
                                        {
                                            "path": "rabbitmq.conf",
                                            "key": "rabbitmq.conf"
                                        },
                                        {
                                            "path": "enabled_plugins",
                                            "key": "enabled_plugins"
                                        }
                                    ],
                                    "name": self.objects_name["ConfigMap"]
                                },
                                "name": "config-volume"
                            }
                        ]
                    }
                }
            }
        }

        api_response = self.__create_object(
            self.apps_api.create_namespaced_stateful_set,
            self.apps_api.delete_namespaced_stateful_set,
            self.apps_api.list_namespaced_stateful_set,
            manifest)
        return api_response

    def create_cluster(self, replicas=3):
        self.__create_namespace()
        self.__create_service_account()
        self.__create_role()
        self.__create_role_binding()
        self.__create_service()
        self.__create_config_map()
        self.__create_statefulset(replicas)

    def update_cluster(self, api_instance, deployment):
        pass

    def delete_cluster(self, name):
        pass

