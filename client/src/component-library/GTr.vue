<script setup lang="ts">
import { BTr } from "bootstrap-vue";
</script>

<template>
    <BTr v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTr>
</template>
