<script setup lang="ts">
import type { GetComponentPropTypes } from "types/utilityTypes";
import { ref } from "vue";

import CarbonEmissionsIcon from "./CarbonEmissionsIcon.vue";

const props = defineProps<{
    heading: string;
    explanation: string;
    value: string | number;
    icon: GetComponentPropTypes<typeof CarbonEmissionsIcon>["icon"];
}>();

const shouldShowInfo = ref(false);

function toggleInfo() {
    shouldShowInfo.value = !shouldShowInfo.value;
}
</script>

<template>
    <button v-b-tooltip.hover :title="props.explanation" @click="toggleInfo">
        <div id="heading">{{ props.heading }}</div>

        <div class="value">
            <CarbonEmissionsIcon :icon="props.icon" />
            <span id="total-emissions">{{ props.value }}</span>
        </div>
        <span v-if="shouldShowInfo">{{ props.explanation }}</span>
    </button>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

button {
    padding: 0.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: #fff;
    gap: 0.5rem;
    border-radius: 12px;
    border: 1px solid $brand-secondary;
}

button:hover {
    background-color: $brand-secondary;
}

.value {
    display: inline-flex;
    align-items: center;
    gap: 1rem;
}

#heading {
    font-size: 1rem;
}

#total-emissions {
    font-size: 1.25rem;
}
</style>
