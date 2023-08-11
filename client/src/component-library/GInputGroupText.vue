<script setup lang="ts">
import { BInputGroupText } from "bootstrap-vue";
</script>

<template>
    <BInputGroupText v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BInputGroupText>
</template>
