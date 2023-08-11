<script setup lang="ts">
import { computed } from "vue";

import { GInput } from "@/component-library";
import { filesDialog } from "@/utils/data";

interface Props {
    value: string;
    mode?: "file" | "directory";
    requireWritable?: boolean;
}

interface SelectableFile {
    url: string;
}

const props = withDefaults(defineProps<Props>(), {
    mode: "file",
    requireWritable: false,
});

const emit = defineEmits<{
    (e: "input", value: string): void;
}>();

const currentValue = computed({
    get() {
        return props.value;
    },
    set(newValue) {
        emit("input", newValue);
    },
});

const selectFile = () => {
    const dialogProps = {
        mode: props.mode,
        requireWritable: props.requireWritable,
    };
    filesDialog((selected: SelectableFile) => {
        currentValue.value = selected?.url;
    }, dialogProps);
};

const placeholder = `Click to select ${props.mode}`;
</script>

<template>
    <GInput v-model="currentValue" class="directory-form-input" :placeholder="placeholder" @click="selectFile" />
</template>
