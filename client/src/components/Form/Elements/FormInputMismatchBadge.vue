<script setup lang="ts">
import { BBadge } from "bootstrap-vue";
</script>

<template>
    <BBadge
        v-b-tooltip.hover.noninteractive
        class="ml-1"
        variant="warning"
        pill
        size="sm"
        title="The value of this input does not match the original/expected request">
        Input Mismatch
    </BBadge>
</template>
