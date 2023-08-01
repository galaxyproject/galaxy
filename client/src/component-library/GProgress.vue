<script setup lang="ts">
import { BProgress } from "bootstrap-vue";
</script>

<template>
    <BProgress v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BProgress>
</template>
