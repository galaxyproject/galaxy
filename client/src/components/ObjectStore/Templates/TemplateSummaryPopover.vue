<script lang="ts" setup>
import type { ObjectStoreTemplateSummary } from "./types";

import TemplateSummary from "./TemplateSummary.vue";

interface Props {
    target: String;
    template: ObjectStoreTemplateSummary;
}

const props = defineProps<Props>();

const popoverPlacement = "rightbottom";
</script>

<template>
    <b-popover :target="target" triggers="hover" boundary="window" :placement="popoverPlacement">
        <template v-slot:title>{{ props.template.name }}</template>
        <TemplateSummary :template="props.template" />
    </b-popover>
</template>
