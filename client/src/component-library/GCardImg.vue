<script setup lang="ts">
import { BCardImg } from "bootstrap-vue";
</script>

<template>
    <BCardImg v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardImg>
</template>
