<script setup lang="ts">
import { computed } from "vue";

import type { FileSourceTemplateSummary } from "@/api/fileSources";

import FileSourceTypeSpan from "@/components/FileSources/FileSourceTypeSpan.vue";
import ConfigurationMarkdown from "@/components/ObjectStore/ConfigurationMarkdown.vue";

interface Props {
    template: FileSourceTemplateSummary;
}

const props = defineProps<Props>();
const fileSourceType = computed(() => props.template.type);
</script>

<template>
    <div>
        <div>This template produces file sources of type <FileSourceTypeSpan :type="fileSourceType" />.</div>
        <ConfigurationMarkdown :markdown="template.description || ''" :admin="true" />
    </div>
</template>
