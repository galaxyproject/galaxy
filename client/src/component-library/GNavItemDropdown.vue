<script setup lang="ts">
import { BNavItemDropdown } from "bootstrap-vue";
</script>

<template>
    <BNavItemDropdown v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNavItemDropdown>
</template>
