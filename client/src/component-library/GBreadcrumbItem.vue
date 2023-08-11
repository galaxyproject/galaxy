<script setup lang="ts">
import { BBreadcrumbItem } from "bootstrap-vue";
</script>

<template>
    <BBreadcrumbItem v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BBreadcrumbItem>
</template>
