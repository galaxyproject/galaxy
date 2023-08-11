<script setup lang="ts">
import { BDropdown } from "bootstrap-vue";
</script>

<template>
    <BDropdown v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BDropdown>
</template>
