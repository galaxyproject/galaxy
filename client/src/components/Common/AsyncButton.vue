<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref } from "vue";

interface Props {
    icon: string | object;
    title?: string;
    disabled?: boolean;
    loadingTitle?: string;
    size?: "sm" | "md" | "lg";
    action: () => Promise<void>;

    variant?:
        | "outline-primary"
        | "primary"
        | "secondary"
        | "success"
        | "danger"
        | "warning"
        | "info"
        | "light"
        | "dark"
        | "link";
}

const props = withDefaults(defineProps<Props>(), {
    title: "",
    size: "md",
    variant: "link",
    loadingTitle: "加载中...",
});

const loading = ref(false);

async function onClick() {
    loading.value = true;
    await props.action();
    loading.value = false;
}
</script>

<template>
    <BButton
        v-b-tooltip.hover.noninteractive="!title"
        :title="title"
        :size="size"
        :variant="variant"
        :disabled="loading || disabled"
        @click="onClick">
        <span v-if="loading" class="loading-icon fa fa-spinner fa-spin" :title="loadingTitle" />
        <FontAwesomeIcon v-else :icon="props.icon" fixed-width />
        <slot></slot>
    </BButton>
</template>
