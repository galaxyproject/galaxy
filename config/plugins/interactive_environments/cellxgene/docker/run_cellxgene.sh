#!/bin/sh

get -i ${DATASET_HID} \
    && mv /import/${DATASET_HID} /import/${DATASET_HID}.h5ad \
    && cellxgene launch --host 0.0.0.0 --port 80 /import/${DATASET_HID}.h5ad
