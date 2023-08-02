<script setup lang="ts">
import { BThead } from "bootstrap-vue";
</script>

<template>
    <BThead v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BThead>
</template>
