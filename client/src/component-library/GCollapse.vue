<script setup lang="ts">
import { BCollapse } from "bootstrap-vue";
</script>

<template>
    <BCollapse v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCollapse>
</template>
