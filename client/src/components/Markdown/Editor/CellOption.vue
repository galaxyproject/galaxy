<template>
    <span role="button" tabindex="0" class="cell-option d-flex justify-content-between" @click="$emit('click')">
        <div class="my-1 mx-3">
            <div class="font-weight-bold">{{ title }}</div>
            <small class="d-inline-block text-wrap text-break">{{ description }}</small>
        </div>
        <div v-if="icon" class="my-2 mx-3 align-self-center">
            <FontAwesomeIcon :icon="icon" />
        </div>
    </span>
</template>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

defineProps<{
    title: string;
    description: string;
    icon?: any;
}>();

defineEmits<{
    (e: "click"): void;
}>();
</script>

<style scoped lang="scss">
@import "theme/blue.scss";

.cell-option {
    &:hover {
        background: $brand-primary;
        color: $white;
        small {
            color: $white;
        }
    }
    small {
        color: $text-muted;
    }
}
</style>
