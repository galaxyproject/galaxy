<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";

import { useMarkdown } from "@/composables/markdown";
import { Toast } from "@/composables/toast";
import { errorMessageAsString } from "@/utils/simple-error";

interface Props {
    historyContentId: string;
}

const props = defineProps<Props>();

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });

const content = ref("");

async function getMarkdownData() {
    try {
        const { data } = await axios.get(`/api/datasets/${props.historyContentId}/display?preview=true`);
        content.value = data;
    } catch (error) {
        console.error("Error fetching dataset content", props.historyContentId, error);
        Toast.error(errorMessageAsString(error));
    }
}

onMounted(async () => {
    await getMarkdownData();
});
</script>

<template>
    <div class="dataset-in-markdown">
        <div v-if="content" v-html="renderMarkdown(content)" />
    </div>
</template>
