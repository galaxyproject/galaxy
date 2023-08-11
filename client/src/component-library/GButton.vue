<script setup lang="ts">
import { BButton } from "bootstrap-vue";
</script>

<template>
    <BButton v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BButton>
</template>
