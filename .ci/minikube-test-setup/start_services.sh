#!/usr/bin/env bash
set -ex

SCRIPTDIR=$(dirname "${BASH_SOURCE[0]}")
kubectl apply -f "$SCRIPTDIR/deployment.yaml"
kubectl expose deployment testing --type=LoadBalancer --name=testing-service

CLUSTER_IP=$(kubectl get service testing-service -o jsonpath='{.spec.clusterIP}')
GALAXY_TEST_DBURI="postgresql://postgres:postgres@${CLUSTER_IP}:5432/galaxy?client_encoding=utf-8"
GALAXY_TEST_AMQP_URL="amqp://${CLUSTER_IP}:5672//"
export GALAXY_TEST_DBURI
export GALAXY_TEST_AMQP_URL
