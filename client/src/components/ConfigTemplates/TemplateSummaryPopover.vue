<script lang="ts" setup>
import type { TemplateSummary } from "@/api/configTemplates";

import GPopover from "@/components/BaseComponents/GPopover.vue";

interface Props {
    target: string;
    template: TemplateSummary;
}

const props = defineProps<Props>();

const popoverPlacement = "rightbottom";
</script>

<template>
    <GPopover :target="target" triggers="hover" boundary="window" :placement="popoverPlacement">
        <template v-slot:title>{{ props.template.name }}</template>
        <slot />
    </GPopover>
</template>
