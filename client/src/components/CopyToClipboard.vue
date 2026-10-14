<script setup lang="ts">
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import type { ComponentSize } from "@/components/BaseComponents/componentVariants";
import { copy } from "@/utils/clipboard";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = withDefaults(
    defineProps<{
        text: string;
        message: string;
        title?: string;
        transparent?: boolean;
        size?: ComponentSize;
    }>(),
    {
        title: "Copy to clipboard",
        transparent: true,
    },
);
</script>

<template>
    <GButton
        :transparent="props.transparent"
        icon-only
        :size="props.size"
        :title="props.title"
        @click="copy(props.text, props.message)">
        <FontAwesomeIcon :icon="faCopy" aria-hidden="true" fixed-width />
    </GButton>
</template>
