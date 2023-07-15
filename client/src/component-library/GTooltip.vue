<script setup lang="ts">
import { BTooltip } from "bootstrap-vue";
</script>

<template>
    <BTooltip v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BTooltip>
</template>
