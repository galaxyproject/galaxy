<script setup lang="ts">
import { BDropdownForm } from "bootstrap-vue";
</script>

<template>
    <BDropdownForm v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BDropdownForm>
</template>
