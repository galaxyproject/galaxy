<script setup>
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";

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
        <font-awesome-icon icon="external-link-alt" />
    </a>
</template>
