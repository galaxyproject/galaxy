<script setup lang="ts">
import { ref } from "vue";

import type { AnyFetchTarget, FetchTargets } from "@/api/tools";

import FetchGrid from "./FetchGrid.vue";

const fetchGrids = ref<unknown[]>([]);

interface TargetComponent {
    asTarget(): AnyFetchTarget;
}

interface Props {
    targets: FetchTargets;
}

function asTargets() {
    const targets = fetchGrids.value.map((fetchGrid) => {
        const component = fetchGrid as TargetComponent;
        return component.asTarget();
    });
    return targets;
}

defineExpose({ asTargets });

defineProps<Props>();
</script>

<template>
    <div>
        <div v-for="(target, index) in targets" :key="index">
            <FetchGrid ref="fetchGrids" :target="target" />
        </div>
    </div>
</template>
