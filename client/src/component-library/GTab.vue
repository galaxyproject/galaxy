<script setup lang="ts">
import { BTab } from "bootstrap-vue";
</script>

<template>
    <BTab v-bind="$attrs" v-on="$listeners">
        <template v-slot:title>
            <slot name="title"></slot>
        </template>

        <slot></slot>
    </BTab>
</template>
