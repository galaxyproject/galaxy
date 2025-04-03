<template>
    <span
        role="button"
        tabindex="0"
        class="cell-option d-flex justify-content-between"
        @click="$emit('click')"
        @keydown.enter="$emit('click')">
        <div class="my-1 mx-3">
            <div class="font-weight-bold">{{ title }}</div>
            <small v-if="description" class="d-inline-block text-wrap text-break">{{ description }}</small>
        </div>
        <div v-if="icon" class="my-2 mx-3 align-self-start">
            <FontAwesomeIcon :icon="icon" class="cell-option-icon" />
        </div>
        <div v-else-if="logo" class="my-2 mx-3 align-self-start">
            <Img class="cell-option-logo" :src="logo" :alt="title" />
        </div>
    </span>
</template>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { IconDefinition } from "font-awesome-6";

defineProps<{
    title: string;
    description: string;
    icon?: IconDefinition;
    logo?: string;
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
    .cell-option-icon {
        font-size: 1rem;
    }
    .cell-option-logo {
        width: 2rem;
    }
}
</style>
