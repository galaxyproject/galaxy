<script setup lang="ts">
import { BFormText } from "bootstrap-vue";
</script>

<template>
    <BFormText v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormText>
</template>
