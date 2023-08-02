<script setup lang="ts">
import { BForm } from "bootstrap-vue";
import { computed, ref } from "vue";

const props = defineProps({
    value: {
        type: Boolean,
        default: null,
    },
});

const emit = defineEmits<{
    (e: "input", value: boolean): void;
}>();

const formRef = ref();

const model = computed({
    get: () => props.value ?? false,
    set: (value) => {
        emit("input", value);
    },
});

function checkValidity() {
    formRef.value.checkValidity();
}

defineExpose({
    checkValidity,
});
</script>

<template>
    <BForm ref="formRef" v-model="model" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BForm>
</template>
