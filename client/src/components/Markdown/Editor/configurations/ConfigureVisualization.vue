<template>
    <ConfigureSelector :content-object="contentObject" @change="onChange($event)" />
</template>

<script setup lang="ts">
import ConfigureSelector from "./ConfigureSelector.vue";

interface ContentType {
    dataset_id: string;
    dataset_name?: string;
}

interface OptionType {
    id: string | null | undefined;
    name: string | null | undefined;
}

const props = defineProps<{
    contentObject: ContentType;
}>();

const emit = defineEmits<{
    (e: "change", content: string): void;
}>();

function onChange(newValue: OptionType) {
    const newValues = { ...props.contentObject, dataset_id: newValue.id, dataset_name: newValue.name };
    emit("change", JSON.stringify(newValues, null, 4));
}
</script>
