<script setup lang="ts">
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";

const props = defineProps<{
    slug: string;
}>();

const emit = defineEmits<{
    (e: "change", newValue: string): void;
}>();

const initialSlug = props.slug;

function onChange(event: Event) {
    const slugFormatted = (event.target as HTMLInputElement).value
        .replace(/\s+/g, "-")
        .replace(/[/:?#]/g, "")
        .toLowerCase();

    emit("change", slugFormatted);
}

function onCancel() {
    emit("change", initialSlug);
}
</script>

<template>
    <GFormInput
        :model-value="props.slug"
        type="text"
        class="d-inline w-auto h-auto px-1 py-0"
        @change="onChange"
        @keydown.esc="onCancel" />
</template>
