<template>
    <div class="cell-option d-flex justify-content-between rounded m-1" @click="$emit('click')">
        <div class="m-2">
            <div class="font-weight-bold">{{ title }}</div>
            <small>{{ description }}</small>
        </div>
        <div v-if="icon" class="m-2 align-self-center">
            <FontAwesomeIcon :icon="icon" />
        </div>
    </div>
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
