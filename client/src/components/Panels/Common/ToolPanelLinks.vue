<script setup lang="ts">
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed } from "vue";

const props = defineProps<{
    links: Record<string, string>;
}>();

const link = computed(() => {
    const links = Object.values(props.links);
    return links.length > 0 ? links[0] : null;
});
</script>

<template>
    <span v-if="link" class="tool-panel-links">
        <a :href="link" target="_blank" style="display: inline">
            <FontAwesomeIcon v-b-tooltip.hover title="Link" :icon="faExternalLinkAlt" />
            <span class="sr-only">Link</span>
        </a>
    </span>
</template>
