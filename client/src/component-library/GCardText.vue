<script setup lang="ts">
import { BCardText } from "bootstrap-vue";
</script>

<template>
    <BCardText v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BCardText>
</template>
