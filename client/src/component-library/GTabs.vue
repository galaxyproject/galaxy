<script setup lang="ts">
import { BTabs } from "bootstrap-vue";
</script>

<template>
    <BTabs v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTabs>
</template>
