<script setup lang="ts">
import { BDropdownItem } from "bootstrap-vue";
</script>

<template>
    <BDropdownItem v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BDropdownItem>
</template>
