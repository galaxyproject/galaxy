<script setup lang="ts">
import { BFormGroup } from "bootstrap-vue";
</script>

<template>
    <BFormGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BFormGroup>
</template>
