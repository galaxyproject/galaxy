<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";

const props = defineProps<{
    slug: string;
}>();

const emit = defineEmits<{
    (e: "change", newValue: string): void;
}>();

// eslint-disable-next-line vue/no-setup-props-destructure
const initialSlug = props.slug;

function onChange(value: string) {
    const slugFormatted = value
        .replace(/\s+/g, "-")
        .replace(/[\/:?#]/g, "")
        .toLowerCase();

    emit("change", slugFormatted);
}

function onCancel() {
    emit("change", initialSlug);
}
</script>

<template>
    <BFormInput
        :value="props.slug"
        type="text"
        class="d-inline w-auto h-auto px-1 py-0"
        @change="onChange"
        @keydown.esc="onCancel" />
</template>
