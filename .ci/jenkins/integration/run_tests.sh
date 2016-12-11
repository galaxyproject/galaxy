#!/bin/bash

./scripts/common_startup.sh --dev-wheels

nosetests test/integration
