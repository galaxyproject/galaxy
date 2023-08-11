<script setup lang="ts">
import { BOverlay } from "bootstrap-vue";
</script>

<template>
    <BOverlay v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BOverlay>
</template>
