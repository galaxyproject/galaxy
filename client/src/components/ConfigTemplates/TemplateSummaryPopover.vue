<script lang="ts" setup>
import { BPopover } from "bootstrap-vue";

import type { TemplateSummary } from "@/api/configTemplates";

interface Props {
    target: String;
    template: TemplateSummary;
}

const props = defineProps<Props>();

const popoverPlacement = "rightbottom";
</script>

<template>
    <BPopover :target="target" triggers="hover" boundary="window" :placement="popoverPlacement">
        <template v-slot:title>{{ props.template.name }}</template>
        <slot />
    </BPopover>
</template>
