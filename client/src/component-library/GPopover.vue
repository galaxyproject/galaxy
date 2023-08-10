<script setup lang="ts">
import { BPopover } from "bootstrap-vue";
</script>

<template>
    <BPopover v-bind="$attrs" v-on="$listeners">
        <template v-for="(_, slot) of $scopedSlots" v-slot:[slot]="scope">
            <slot :name="slot" v-bind="scope" />
        </template>
    </BPopover>
</template>
