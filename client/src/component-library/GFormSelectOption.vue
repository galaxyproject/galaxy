<script setup lang="ts">
import { BFormSelectOption } from "bootstrap-vue";
</script>

<template>
    <BFormSelectOption v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormSelectOption>
</template>
