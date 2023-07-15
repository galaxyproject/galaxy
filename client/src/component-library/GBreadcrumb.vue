<script setup lang="ts">
import { BBreadcrumb } from "bootstrap-vue";
</script>

<template>
    <BBreadcrumb v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BBreadcrumb>
</template>
