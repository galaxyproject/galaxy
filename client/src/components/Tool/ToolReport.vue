<script setup lang="ts">
import { computed, ref } from "vue";

import { useConfig } from "@/composables/config";
import { urlData } from "@/utils/url";

import Markdown from "@/components/Markdown/Markdown.vue";

interface Props {
    datasetId: string;
}

const props = defineProps<Props>();

const dataUrl = computed(() => {
    return `/api/datasets/${props.datasetId}/report`;
});

const dataRef = ref<unknown>(null);

const { config, isConfigLoaded } = useConfig(true);

urlData({ url: dataUrl.value }).then((data) => {
    dataRef.value = data;
});
</script>

<template>
    <div>
        <Markdown
            v-if="isConfigLoaded && dataRef"
            :markdown-config="dataRef"
            :enable-beta-markdown-export="config.enable_beta_markdown_export"
            download-endpoint="TODO"
            :show-identifier="false"
            :read-only="true" />
        <div v-else>Loading....</div>
    </div>
</template>
