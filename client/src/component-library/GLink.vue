<script setup lang="ts">
import { BLink } from "bootstrap-vue";
</script>

<template>
    <BLink v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BLink>
</template>
