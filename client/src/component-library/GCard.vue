<script setup lang="ts">
import { BCard } from "bootstrap-vue";
</script>

<template>
    <BCard v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCard>
</template>
