<script setup lang="ts">
import CarbonEmissionsIcon from "./CarbonEmissionsIcon.vue";

export interface CarbonEmissionsCardProps {
    heading: string;
    explanation: string;
    value: string | number;
    icon: InstanceType<typeof CarbonEmissionsIcon>["$props"]["icon"];
}

const props = defineProps<CarbonEmissionsCardProps>();
</script>

<template>
    <div v-b-tooltip.hover :title="props.explanation" class="usage">
        <div id="heading">{{ props.heading }}</div>

        <div class="value">
            <CarbonEmissionsIcon :icon="props.icon" />
            <span id="total-emissions">{{ props.value }}</span>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.usage {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    height: 7rem;
    border-radius: 12px;
    border: 1px solid $brand-secondary;
}

.usage:hover {
    cursor: help;
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
