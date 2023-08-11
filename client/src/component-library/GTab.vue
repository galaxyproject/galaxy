<script setup lang="ts">
import { BTab } from "bootstrap-vue";
</script>

<template>
    <BTab v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BTab>
</template>
