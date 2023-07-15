<script setup lang="ts">
import { BTab } from "bootstrap-vue";
</script>

<template>
    <BTab v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTab>
</template>
