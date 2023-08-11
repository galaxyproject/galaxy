<script setup lang="ts">
import { BDropdownGroup } from "bootstrap-vue";
</script>

<template>
    <BDropdownGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BDropdownGroup>
</template>
