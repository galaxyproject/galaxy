<script setup lang="ts">
import { BPagination } from "bootstrap-vue";
</script>

<template>
    <BPagination v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BPagination>
</template>
