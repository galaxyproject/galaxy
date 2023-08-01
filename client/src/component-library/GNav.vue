<script setup lang="ts">
import { BNav } from "bootstrap-vue";
</script>

<template>
    <BNav v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BNav>
</template>
