<script setup lang="ts">
import { BContainer } from "bootstrap-vue";
</script>

<template>
    <BContainer v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BContainer>
</template>
