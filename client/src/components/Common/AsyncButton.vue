<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { ref } from "vue";

const loading = ref(false);

const props = defineProps({
    icon: {
        type: String,
        required: true,
    },
    title: {
        type: String,
        required: false,
        default: "",
    },
    action: {
        type: Function,
        required: true,
    },
    size: {
        type: String,
        required: false,
        default: "md",
    },
    variant: {
        type: String,
        required: false,
        default: "link",
    },
    disabled: {
        type: Boolean,
        required: false,
        default: false,
    },
});

async function onClick() {
    loading.value = true;
    await props.action();
    loading.value = false;
}
</script>

<template>
    <BButton
        v-b-tooltip.hover="!title"
        :title="title"
        :size="size"
        :variant="variant"
        :disabled="loading || disabled"
        @click="onClick">
        <span v-if="loading" class="loading-icon fa fa-spinner fa-spin" title="loading"></span>
        <FontAwesomeIcon v-else :icon="props.icon" @click="onClick" />
        <slot></slot>
    </BButton>
</template>
