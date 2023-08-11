<script setup lang="ts">
import { BNavbarNav } from "bootstrap-vue";
</script>

<template>
    <BNavbarNav v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNavbarNav>
</template>
