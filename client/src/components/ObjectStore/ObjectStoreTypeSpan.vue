<script setup lang="ts">
import { computed } from "vue";

import { type ObjectStoreTemplateType } from "@/api/objectStores";

const MESSAGES = {
    aws_s3: "这是基于亚马逊简单存储服务（S3）的存储位置。此处的数据由亚马逊托管。",
    azure_blob:
        "这是基于微软Azure Blob的存储位置。关于微软Azure Blob存储的更多信息可在 https://azure.microsoft.com/en-us/products/storage/blobs/ 找到。",
    disk: "这是一个简单的基于路径的存储位置，假定所有相关路径已经在Galaxy服务器和目标工作节点上挂载。",
    boto3: "这是基于亚马逊简单存储服务（S3）接口的存储位置，但可能不是由亚马逊存储。AWS接口已成为行业标准，许多存储供应商支持它并使用它来提供基于对象的存储。",
    generic_s3:
        "这是基于亚马逊简单存储服务（S3）接口的存储位置，但可能不是由亚马逊存储。AWS接口已成为行业标准，许多存储供应商支持它并使用它来提供基于对象的存储。",
    onedata: "这是基于Onedata系统的存储位置。",
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
