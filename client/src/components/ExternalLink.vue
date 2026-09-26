<script setup lang="ts">
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import GLink from "@/components/BaseComponents/GLink.vue";

const props = defineProps<{
    href: string;
}>();
</script>

<template>
    <GLink target="_blank" :href="props.href">
        <slot></slot>
        <FontAwesomeIcon :icon="faExternalLinkAlt" />
    </GLink>
</template>
