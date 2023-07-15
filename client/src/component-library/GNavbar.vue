<script setup lang="ts">
import { BNavbar } from "bootstrap-vue";
</script>

<template>
    <BNavbar v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNavbar>
</template>
