<script setup lang="ts">
import { BListGroupItem } from "bootstrap-vue";
import { ref } from "vue";

const listGroupRef = ref();

function blur() {
    listGroupRef.value.blur();
}

function focus() {
    listGroupRef.value.focus();
}

defineExpose({
    blur,
    focus,
});
</script>

<template>
    <BListGroupItem ref="listGroupRef" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BListGroupItem>
</template>
