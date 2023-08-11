<script setup lang="ts">
import { BTd } from "bootstrap-vue";
</script>

<template>
    <BTd v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTd>
</template>
