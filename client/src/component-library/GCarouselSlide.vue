<script setup lang="ts">
import { BCarouselSlide } from "bootstrap-vue";
</script>

<template>
    <BCarouselSlide v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCarouselSlide>
</template>
