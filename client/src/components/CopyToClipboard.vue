<script setup lang="ts">
import { faCopy } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { copy } from "@/utils/clipboard";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    text: string;
    message: string;
    title?: string;
}>();
</script>

<template>
    <GButton transparent icon-only :title="props.title" @click="copy(props.text, props.message)">
        <FontAwesomeIcon :icon="faCopy" aria-hidden="true" />
    </GButton>
</template>
