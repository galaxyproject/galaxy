<script setup lang="ts">
import { BCardHeader } from "bootstrap-vue";
</script>

<template>
    <BCardHeader v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardHeader>
</template>
