<script setup lang="ts">
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

interface Props {
    id: string;
    full?: boolean;
    title?: string;
    disabled?: boolean;
    version?: number;
    force?: boolean;
    variant?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: undefined,
    version: undefined,
    variant: "primary",
});

const runPath = computed(
    () => `/workflows/run?id=${props.id}${props.version !== undefined ? `&version=${props.version}` : ""}`
);

function forceRunPath() {
    if (props.force) {
        window.open(runPath.value);
    }
}
</script>

<template>
    <BButton
        id="workflow-run-button"
        v-b-tooltip.hover.top.html.noninteractive
        :title="title ?? 'Run workflow'"
        :data-workflow-run="id"
        :variant="variant"
        size="sm"
        class="text-decoration-none"
        :disabled="disabled"
        :to="runPath"
        @click="forceRunPath">
        <FontAwesomeIcon :icon="faPlay" fixed-width />

        <span v-if="full" v-localize>Run</span>
    </BButton>
</template>
