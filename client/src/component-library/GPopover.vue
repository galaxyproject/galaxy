<script setup lang="ts">
import { BPopover } from "bootstrap-vue";
</script>

<template>
    <BPopover v-bind="$attrs" v-on="$listeners">
        <template v-slot:title>
            <slot name="title"></slot>
        </template>

        <slot></slot>
    </BPopover>
</template>
