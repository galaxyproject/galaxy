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
        :title="tooltip | l"
        @click="emit('click')">
        <template>
            <div class="nav-icon m-0 p-0">
                <Icon :icon="icon" />
            </div>
            <div class="nav-title">{{ title }}</div>
        </template>
    </b-nav-item>
</template>

<style scoped>
@import "theme/blue.scss";

.nav-item-active {
    border-radius: 0.5rem;
    background: $gray-300;
}

.nav-icon {
    height: 2rem;
    display: flex;
    align-items: center;
    align-content: center;
    justify-content: center;
}

.nav-title {
    font-size: 0.7rem;
}
</style>
