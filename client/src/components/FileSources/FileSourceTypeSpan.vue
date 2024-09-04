<script setup lang="ts">
import { computed } from "vue";

import type { FileSourceTypes } from "@/api/fileSources";

const MESSAGES = {
    posix: "This is a simple path based storage location that assumes the all the relevant paths are already mounted on the Galaxy server and target worker nodes.",
    s3fs: "This is an remote file source plugin based on the Amazon Simple Storage Service (S3) interface. The AWS interface has become an industry standard and many storage vendors support it and use it to expose 'object' based storage.",
    azure: "This is an remote file source plugin based on the Azure service.",
    onedata: "This is an remote file source plugin based on the Onedata service.",
    ftp: "This is an remote file source plugin based on the FTP protocol.",
};

interface Props {
    type: FileSourceTypes;
}

const props = defineProps<Props>();
const title = computed<string>(() => MESSAGES[props.type] ?? "");
</script>

<template>
    <span v-b-tooltip.hover class="file-source-type file-source-help-on-hover" :title="title">{{ type }}</span>
</template>

<style scoped>
@import "./style.css";
</style>
