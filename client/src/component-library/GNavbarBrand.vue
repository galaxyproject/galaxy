<script setup lang="ts">
import { BNavbarBrand } from "bootstrap-vue";
</script>

<template>
    <BNavbarBrand v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNavbarBrand>
</template>
