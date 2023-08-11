<script setup lang="ts">
import { BCard } from "bootstrap-vue";
</script>

<template>
    <BCard v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BCard>
</template>
