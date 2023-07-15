<script setup lang="ts">
import { BEmbed } from "bootstrap-vue";
</script>

<template>
    <BEmbed v-bind="$attrs" v-on="$listeners">
        <slot></slot>
    </BEmbed>
</template>
