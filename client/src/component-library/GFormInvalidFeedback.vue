<script setup lang="ts">
import { BFormInvalidFeedback } from "bootstrap-vue";
</script>

<template>
    <BFormInvalidFeedback v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormInvalidFeedback>
</template>
