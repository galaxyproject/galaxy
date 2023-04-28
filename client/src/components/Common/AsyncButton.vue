<script setup lang="ts">
import { ref } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const loading = ref(false);

const props = defineProps({
    icon: {
        type: String,
        required: true,
    },
    action: {
        type: Function,
        required: true,
    },
    size: {
        type: String,
        required: false,
        default: "sm",
    },
    variant: {
        type: String,
        required: false,
        default: "link",
    },
});

async function onClick() {
    loading.value = true;
    await props.action();
    loading.value = false;
}
</script>

<template>
    <BButton :size="size" :variant="variant" @click="onClick" :disabled="loading">
        <span v-if="loading" class="loading-icon fa fa-spinner fa-spin" title="loading"></span>
        <FontAwesomeIcon v-else :icon="props.icon" @click="onClick" />
        <slot></slot>
    </BButton>
</template>
