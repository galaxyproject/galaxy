<script setup lang="ts">
import { BTableLite } from "bootstrap-vue";
</script>

<template>
    <BTableLite v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BTableLite>
</template>
