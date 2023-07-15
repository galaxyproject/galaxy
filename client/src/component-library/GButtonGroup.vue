<script setup lang="ts">
import { BButtonGroup } from "bootstrap-vue";
</script>

<template>
    <BButtonGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BButtonGroup>
</template>
