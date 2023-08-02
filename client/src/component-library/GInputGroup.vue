<script setup lang="ts">
import { BInputGroup } from "bootstrap-vue";
</script>

<template>
    <BInputGroup v-bind="$attrs" v-on="$listeners">
        <template v-slot:append>
            <slot name="append"></slot>
        </template>

        <slot></slot>
    </BInputGroup>
</template>
