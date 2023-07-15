<script setup lang="ts">
import { BInputGroup } from "bootstrap-vue";
</script>

<template>
    <BInputGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BInputGroup>
</template>
