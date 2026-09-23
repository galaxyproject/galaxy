<script setup lang="ts">
import { BAlert, BCard } from "bootstrap-vue";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useMarkdown } from "@/composables/markdown";

import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    workflow?: StoredWorkflowDetailed;
    loading?: boolean;
}>();

const { renderMarkdown } = useMarkdown({
    openLinksInNewPage: true,
    removeNewlinesAfterList: true,
    increaseHeadingLevelBy: 2,
});
</script>

<template>
    <BAlert v-if="props.loading" variant="info" show>
        <LoadingSpan message="Loading workflow help" />
    </BAlert>
    <BCard v-else-if="props.workflow" class="mx-1 flex-grow-1 overflow-auto">
        <p
            v-if="props.workflow.readme"
            v-sanitize-html:links="renderMarkdown(props.workflow.readme)"
            class="container" />
        <template v-if="props.workflow.help">
            <hr v-if="props.workflow.readme" class="w-100" />
            <h4 class="text-center">Workflow Help</h4>
            <p v-sanitize-html:links="renderMarkdown(props.workflow.help)" class="container" />
        </template>
        <div class="py-2 text-center">- End of help -</div>
    </BCard>
</template>
