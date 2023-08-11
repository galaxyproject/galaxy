<script setup lang="ts">
import { BFormDatalist } from "bootstrap-vue";
</script>

<template>
    <BFormDatalist v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormDatalist>
</template>
