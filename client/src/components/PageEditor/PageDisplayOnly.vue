<script setup lang="ts">
import type { PAGE_LABELS } from "@/components/Page/constants";

import type { MarkdownConfig } from "../Markdown/types.js";

import Markdown from "../Markdown/Markdown.vue";
import PageDisplayToolbar from "./PageDisplayToolbar.vue";

const props = defineProps<{
    labels: (typeof PAGE_LABELS)[keyof typeof PAGE_LABELS];
    markdownConfig?: MarkdownConfig;
    hideHeader?: boolean;
}>();

const emit = defineEmits<{
    (e: "edit"): void;
    (e: "back"): void;
}>();
</script>

<template>
    <div class="d-flex flex-column">
        <PageDisplayToolbar
            v-if="!props.hideHeader"
            :labels="props.labels"
            mode="display"
            @edit="emit('edit')"
            @back="emit('back')" />
        <div class="page-display-content" data-description="page rendered view">
            <Markdown
                v-if="markdownConfig"
                class="px-3 pt-3"
                :markdown-config="markdownConfig"
                read-only
                no-heading
                download-endpoint="" />
        </div>
    </div>
</template>

<style scoped>
.page-display-content {
    overflow: auto;
    flex: 1 1 0;
}
</style>
