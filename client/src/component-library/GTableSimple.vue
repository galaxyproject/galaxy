<script setup lang="ts">
import { BTableSimple } from "bootstrap-vue";
</script>

<template>
    <BTableSimple v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTableSimple>
</template>
