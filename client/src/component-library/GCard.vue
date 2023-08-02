<script setup lang="ts">
import { BCard } from "bootstrap-vue";
</script>

<template>
    <BCard v-bind="$attrs" v-on="$listeners">
        <template v-slot:header>
            <slot name="header"></slot>
        </template>

        <slot></slot>
    </BCard>
</template>
