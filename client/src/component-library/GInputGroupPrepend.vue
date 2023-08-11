<script setup lang="ts">
import { BInputGroupPrepend } from "bootstrap-vue";
</script>

<template>
    <BInputGroupPrepend v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BInputGroupPrepend>
</template>
