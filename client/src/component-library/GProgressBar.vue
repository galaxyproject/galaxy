<script setup lang="ts">
import { BProgressBar } from "bootstrap-vue";
</script>

<template>
    <BProgressBar v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BProgressBar>
</template>
