<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { ComponentColor } from "../BaseComponents/componentVariants";

import GButton from "../BaseComponents/GButton.vue";

interface Props {
    icon: string | object;
    title?: string;
    disabled?: boolean;
    loadingTitle?: string;
    size?: "small" | "medium" | "large";
    action: () => Promise<void>;
    transparent?: boolean;
    outline?: boolean;
    color?: ComponentColor;
}

const props = withDefaults(defineProps<Props>(), {
    title: "",
    size: "medium",
    color: "blue",
    loadingTitle: "Loading...",
});

const loading = ref(false);

async function onClick() {
    loading.value = true;
    await props.action();
    loading.value = false;
}
</script>

<template>
    <GButton
        :tooltip="Boolean(title)"
        :title="loading ? loadingTitle : title"
        :size="size"
        :color="color"
        :transparent="transparent"
        :disabled="loading || disabled"
        @click="onClick">
        <span v-if="loading" class="loading-icon fa fa-spinner fa-spin" />
        <FontAwesomeIcon v-else :icon="props.icon" fixed-width />
        <slot></slot>
    </GButton>
</template>
