<script setup lang="ts">
import { ref } from "vue";

import { assertDefined } from "@/utils/assertions";

const form = ref<HTMLFormElement>();

function checkValidity() {
    assertDefined(form.value);
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

<style scoped lang="scss"></style>
