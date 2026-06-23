<script lang="ts" setup>
import type { ObjectStoreTemplateSummary } from "./types";

import TemplateSummary from "./TemplateSummary.vue";
import TemplateSummaryPopover from "@/components/ConfigTemplates/TemplateSummaryPopover.vue";

interface Props {
    target: String;
    template: ObjectStoreTemplateSummary;
}

defineProps<Props>();
</script>

<template>
    <TemplateSummaryPopover :target="target" :template="template">
        <TemplateSummary :template="template" />
    </TemplateSummaryPopover>
</template>
