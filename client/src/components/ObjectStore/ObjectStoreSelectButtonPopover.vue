<script setup lang="ts">
import GPopover from "@/components/BaseComponents/GPopover.vue";

interface ObjectStoreSelectButtonPopoverProps {
    target: string;
    title: string;
}

defineProps<ObjectStoreSelectButtonPopoverProps>();

const boundary = "window"; // don't warp the popover to squeeze it into this modal
</script>

<template>
    <GPopover :target="target" triggers="hover" placement="rightbottom" :boundary="boundary">
        <template v-slot:title>{{ title }}</template>
        <slot />
    </GPopover>
</template>
