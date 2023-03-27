<script setup lang="ts">
import { ref } from "vue";

export interface Props {
    id: string;
    title: string;
    icon?: string;
    isActive?: boolean;
    tooltip?: string;
}

const props = withDefaults(defineProps<Props>(), {
    icon: "question",
    isActive: false,
    tooltip: null,
});

const emit = defineEmits<{
    (e: "click"): void;
}>();
</script>

<template>
    <b-nav-item
        :id="id"
        :class="{ 'nav-item-active': isActive }"
        :aria-label="title | l"
        :title="tooltip | l"
        @click="emit('click')">
        <template>
            <div class="nav-icon">
                <Icon :icon="icon" />
            </div>
            <div class="nav-title">{{ title }}</div>
        </template>
    </b-nav-item>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.nav-item {
    display: flex;
    align-items: center;
    align-content: center;
    justify-content: center;
}

.nav-item-active {
    border-radius: $border-radius-extralarge;
    background: $gray-300;
}

.nav-icon {
    @extend .nav-item;
    font-size: 1rem;
}

.nav-title {
    @extend .nav-item;
    font-size: 0.7rem;
}
</style>
