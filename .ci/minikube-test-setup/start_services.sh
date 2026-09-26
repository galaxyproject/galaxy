#!/usr/bin/env bash
set -ex

SCRIPTDIR=$(dirname "${BASH_SOURCE[0]}")
kubectl apply -f "$SCRIPTDIR/deployment.yaml"
kubectl expose deployment testing --type=LoadBalancer --name=testing-service

# Wait for the postgres + rabbitmq pod to actually be Ready before letting
# tests run. The Service ClusterIP is reserved as soon as ``kubectl expose``
# returns, but the underlying container image pull + container start can
# take 30+ seconds — long enough that the first test may race the pod and
# hit ``Connection refused`` before the postgres listener is up. That race
# wipes out the entire shard (every Galaxy boot fails to talk to its DB).
kubectl rollout status deployment/testing --timeout=300s
kubectl wait --for=condition=Ready --timeout=300s pod -l app.kubernetes.io/name=test

CLUSTER_IP=$(kubectl get service testing-service -o jsonpath='{.spec.clusterIP}')
GALAXY_TEST_DBURI="postgresql+psycopg://postgres:postgres@${CLUSTER_IP}:5432/galaxy?client_encoding=utf-8"
GALAXY_TEST_AMQP_URL="amqp://${CLUSTER_IP}:5672//"
export GALAXY_TEST_DBURI
export GALAXY_TEST_AMQP_URL
