<script setup lang="ts">
import { BCardTitle } from "bootstrap-vue";
</script>

<template>
    <BCardTitle v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardTitle>
</template>
