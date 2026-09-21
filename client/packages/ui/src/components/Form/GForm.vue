<script setup lang="ts">
import { ref } from "vue";

const form = ref<HTMLFormElement>();

function checkValidity() {
    if (!form.value) {
        throw new TypeError("GForm: form element is not mounted");
    }
    return form.value.checkValidity();
}

defineExpose({
    checkValidity,
});
</script>

<template>
    <form ref="form">
        <slot></slot>
    </form>
</template>
