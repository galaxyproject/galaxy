<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faExternalLinkAlt);

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
        <FontAwesomeIcon icon="external-link-alt" />
    </a>
</template>
