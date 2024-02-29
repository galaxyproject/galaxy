<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";

library.add(faPlay);

interface Props {
    id: string;
    full?: boolean;
    title?: string;
    disabled?: boolean;
}

defineProps<Props>();
</script>

<template>
    <BButton
        id="workflow-run-button"
        v-b-tooltip.hover.top.noninteractive
        :title="title ?? 'Run workflow'"
        :data-workflow-run="id"
        variant="primary"
        size="sm"
        :disabled="disabled"
        :to="`/workflows/run?id=${id}`">
        <FontAwesomeIcon :icon="faPlay" fixed-width />

        <span v-if="full" v-localize>Run</span>
    </BButton>
</template>
