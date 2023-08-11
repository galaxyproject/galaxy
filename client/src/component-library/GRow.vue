<script setup lang="ts">
import { BRow } from "bootstrap-vue";
</script>

<template>
    <BRow v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BRow>
</template>
