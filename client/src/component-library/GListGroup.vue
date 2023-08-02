<script setup lang="ts">
import { BListGroup } from "bootstrap-vue";
</script>

<template>
    <BListGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BListGroup>
</template>
