<script setup lang="ts">
import { faExpand, faWindowMaximize } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { computed, ref } from "vue";

import VisualizationFrame from "@/components/Visualizations/VisualizationFrame.vue";

const props = withDefaults(
    defineProps<{
        config: object;
        name: string;
        title?: string;
        height?: number;
    }>(),
    {
        height: 400,
        title: "visualization",
    },
);

const emit = defineEmits<{
    (event: "change", payload: Record<string, any>): void;
    (event: "load"): void;
}>();

const errorMessage = ref("");
const expand = ref(false);

const fixedHeight = computed(() =>
    expand.value ? {} : { maxHeight: `${props.height}px`, minHeight: `${props.height}px` },
);
</script>

<template>
    <div v-if="errorMessage">
        <BAlert variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <div v-else class="position-relative h-100">
        <div :class="`visualization-pop${expand ? 'out' : 'in'}`">
            <VisualizationFrame
                :title="title"
                :config="props.config"
                :name="props.name"
                :style="fixedHeight"
                @change="emit('change', $event)"
                @load="emit('load')" />
        </div>
        <BButton
            class="visualization-popout-expand"
            variant="link"
            size="sm"
            title="Maximize"
            @click="expand = !expand">
            <FontAwesomeIcon :icon="faExpand" />
        </BButton>
        <BButton
            v-if="expand"
            class="visualization-popout-close"
            variant="link"
            size="sm"
            title="Minimize"
            @click="expand = !expand">
            <FontAwesomeIcon :icon="faWindowMaximize" />
        </BButton>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.visualization-popin {
    border: none;
    width: 100%;
    padding-top: 1.5rem;
}
.visualization-popout {
    background: $white;
    border: $border-default;
    border-radius: $border-radius-base;
    height: calc(100vh - 2rem);
    left: 1rem;
    padding-top: 1.5rem;
    position: fixed;
    top: 1rem;
    width: calc(100vw - 2rem);
    z-index: 1000;
}
.visualization-popout-close {
    left: 1rem;
    position: fixed;
    margin: 0.2rem;
    padding: 0 0.5rem;
    top: 1rem;
    z-index: 1001;
}
.visualization-popout-expand {
    left: 0;
    padding: 0 0.5rem;
    position: absolute;
    top: 0;
}
</style>
