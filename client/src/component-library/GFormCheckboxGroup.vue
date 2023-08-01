<script setup lang="ts">
import { BFormCheckboxGroup } from "bootstrap-vue";
</script>

<template>
    <BFormCheckboxGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormCheckboxGroup>
</template>
