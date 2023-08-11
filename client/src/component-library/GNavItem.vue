<script setup lang="ts">
import { BNavItem } from "bootstrap-vue";
</script>

<template>
    <BNavItem v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNavItem>
</template>
