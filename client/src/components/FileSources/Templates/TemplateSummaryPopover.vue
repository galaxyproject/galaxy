<script lang="ts" setup>
import type { FileSourceTemplateSummary } from "@/api/fileSources";

import TemplateSummary from "./TemplateSummary.vue";
import TemplateSummaryPopover from "@/components/ConfigTemplates/TemplateSummaryPopover.vue";

interface Props {
    target: String;
    template: FileSourceTemplateSummary;
}

defineProps<Props>();
</script>

<template>
    <TemplateSummaryPopover :target="target" :template="template">
        <TemplateSummary :template="template" />
    </TemplateSummaryPopover>
</template>
