<script setup lang="ts">
import { BDropdownText } from "bootstrap-vue";
</script>

<template>
    <BDropdownText v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BDropdownText>
</template>
