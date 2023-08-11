<script setup lang="ts">
import { BImg } from "bootstrap-vue";
</script>

<template>
    <BImg v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BImg>
</template>
