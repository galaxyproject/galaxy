<script setup lang="ts">
import { BInputGroup } from "bootstrap-vue";
</script>

<template>
    <BInputGroup v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BInputGroup>
</template>
