<script setup lang="ts">
import { BCardGroup } from "bootstrap-vue";
</script>

<template>
    <BCardGroup v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardGroup>
</template>
