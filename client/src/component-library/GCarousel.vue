<script setup lang="ts">
import { BCarousel } from "bootstrap-vue";
</script>

<template>
    <BCarousel v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCarousel>
</template>
