<script setup lang="ts">
import { computed } from "vue";

import type { ObjectStoreTemplateType } from "@/api/objectStores";

const MESSAGES = {
    aws_s3: "This is a Galaxy storage based on the Amazon Simple Storage Service (S3). Data here is hosted by Amazon.",
    azure_blob:
        "This is a Microsoft Azure Blob based Galaxy storage. More information on Microsoft's Azure Blob Storage can be found at https://azure.microsoft.com/en-us/products/storage/blobs/.",
    disk: "This is a simple path based Galaxy storage that assumes the all the relevant paths are already mounted on the Galaxy server and target worker nodes.",
    boto3: "This is a Galaxy storage based on the Amazon Simple Storage Service (S3) interface, but likely not stored by Amazon. The AWS interface has become an industry standard and many storage vendors support it and use it to expose object based storage.",
    generic_s3:
        "This is a Galaxy storage based on the Amazon Simple Storage Service (S3) interface, but likely not stored by Amazon. The AWS interface has become an industry standard and many storage vendors support it and use it to expose object based storage.",
    onedata: "This is a Galaxy storage based on the Onedata system.",
    rucio: "This is a Galaxy storage based on the RUCIO system https://rucio.cern.ch/.",
    irods: "This is a Galaxy storage based on the iRODS system.",
};

interface Props {
    type: ObjectStoreTemplateType;
}

const props = defineProps<Props>();
const title = computed<string>(() => MESSAGES[props.type] ?? "");
</script>

<template>
    <span v-b-tooltip.hover class="object-store-type object-store-help-on-hover" :title="title">{{ type }}</span>
</template>

<style scoped>
@import "./style.css";
</style>
