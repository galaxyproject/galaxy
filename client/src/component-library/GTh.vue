<script setup lang="ts">
import { BTh } from "bootstrap-vue";
</script>

<template>
    <BTh v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTh>
</template>
