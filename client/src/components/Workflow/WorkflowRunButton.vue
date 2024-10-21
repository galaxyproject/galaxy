<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

library.add(faPlay);

interface Props {
    id: string;
    full?: boolean;
    title?: string;
    disabled?: boolean;
    version?: number;
}

const props = defineProps<Props>();

const runPath = computed(
    () => `/workflows/run?id=${props.id}${props.version !== undefined ? `&version=${props.version}` : ""}`
);
</script>

<template>
    <BButton
        id="workflow-run-button"
        v-b-tooltip.hover.top.html.noninteractive
        :title="title ?? 'Run workflow'"
        :data-workflow-run="id"
        variant="primary"
        size="sm"
        :disabled="disabled"
        :to="runPath">
        <FontAwesomeIcon :icon="faPlay" fixed-width />

        <span v-if="full" v-localize>Run</span>
    </BButton>
</template>
