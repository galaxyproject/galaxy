<script setup lang="ts">
import { BButtonToolbar } from "bootstrap-vue";
</script>

<template>
    <BButtonToolbar v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BButtonToolbar>
</template>
