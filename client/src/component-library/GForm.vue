<script setup lang="ts">
import { BForm } from "bootstrap-vue";
import { ref } from "vue";

const formRef = ref();

function checkValidity() {
    formRef.value.checkValidity();
}

defineExpose({
    checkValidity,
});
</script>

<template>
    <BForm ref="formRef" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BForm>
</template>
