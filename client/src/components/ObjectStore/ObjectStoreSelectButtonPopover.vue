<script setup lang="ts">
import { BPopover } from "bootstrap-vue";

interface ObjectStoreSelectButtonPopoverProps {
    target: string;
    title: string;
}

defineProps<ObjectStoreSelectButtonPopoverProps>();

const boundary = "window"; // don't warp the popover to squeeze it into this modal
</script>

<template>
    <BPopover :target="target" triggers="hover" placement="rightbottom" :boundary="boundary">
        <template v-slot:title>{{ title }}</template>
        <slot />
    </BPopover>
</template>
