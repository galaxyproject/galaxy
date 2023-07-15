<script setup lang="ts">
import { BCardFooter } from "bootstrap-vue";
</script>

<template>
    <BCardFooter v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardFooter>
</template>
