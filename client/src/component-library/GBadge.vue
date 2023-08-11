<script setup lang="ts">
import { BBadge } from "bootstrap-vue";
</script>

<template>
    <BBadge v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BBadge>
</template>
