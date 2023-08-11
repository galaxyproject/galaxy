<script setup lang="ts">
import { BTbody } from "bootstrap-vue";
</script>

<template>
    <BTbody v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTbody>
</template>
