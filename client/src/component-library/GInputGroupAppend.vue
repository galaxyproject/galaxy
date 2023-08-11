<script setup lang="ts">
import { BInputGroupAppend } from "bootstrap-vue";
</script>

<template>
    <BInputGroupAppend v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BInputGroupAppend>
</template>
