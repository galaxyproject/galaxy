<script setup>
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
    href: {
        type: String,
        required: true,
    },
});
</script>

<template>
    <a target="_blank" :href="props.href">
        <slot></slot>
        <FontAwesomeIcon :icon="faExternalLinkAlt" />
    </a>
</template>
