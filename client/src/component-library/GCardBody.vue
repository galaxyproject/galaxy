<script setup lang="ts">
import { BCardBody } from "bootstrap-vue";
</script>

<template>
    <BCardBody v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardBody>
</template>
