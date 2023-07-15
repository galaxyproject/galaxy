<script setup lang="ts">
import { BDropdown } from "bootstrap-vue";
</script>

<template>
    <BDropdown v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BDropdown>
</template>
