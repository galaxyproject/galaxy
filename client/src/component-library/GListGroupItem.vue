<script setup lang="ts">
import { BListGroupItem } from "bootstrap-vue";
import { ref } from "vue";

const listGroupRef = ref();

function focus() {
    listGroupRef.value.focus();
}

function blur() {
    listGroupRef.value.blur();
}

defineExpose({});
</script>

<template>
    <BListGroupItem ref="listGroupRef" v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BListGroupItem>
</template>
