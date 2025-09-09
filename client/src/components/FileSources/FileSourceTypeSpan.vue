<script setup lang="ts">
import { computed } from "vue";

import type { FileSourceTypes } from "@/api/fileSources";
import { templateTypes } from "@/api/fileSources";

const MESSAGES = Object.fromEntries(
    Object.entries(templateTypes).map(([type, { message }]) => [type, message]),
) as Record<FileSourceTypes, string>;

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
