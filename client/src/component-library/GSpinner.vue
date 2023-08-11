<script setup lang="ts">
import { BSpinner } from "bootstrap-vue";
</script>

<template>
    <BSpinner v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BSpinner>
</template>
