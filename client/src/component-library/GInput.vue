<script setup lang="ts">
import { BFormInput } from "bootstrap-vue";
import { computed, ref } from "vue";

interface Props {
    value?: string | number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: Props["value"]): void;
}>();

const formInputRef = ref();

const model = computed({
    get: () => props.value,
    set: (value) => {
        emit("input", value);
    },
});

function blur() {
    formInputRef.value.blur();
}

function focus() {
    formInputRef.value.focus();
}

function select() {
    formInputRef.value.select();
}

defineExpose({
    blur,
    focus,
    select,
});
</script>

<template>
    <BFormInput ref="formInputRef" v-model="model" v-bind="$attrs" v-on="$listeners"> </BFormInput>
</template>
