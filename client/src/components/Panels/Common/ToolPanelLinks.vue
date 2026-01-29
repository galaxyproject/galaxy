<template>
    <span v-if="link" class="tool-panel-links">
        <a :href="link" target="_blank" style="display: inline">
            <FontAwesomeIcon v-b-tooltip.hover title="Link" icon="external-link-alt" />
            <span class="sr-only">Link</span>
        </a>
    </span>
</template>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faExternalLinkAlt);

export default {
    components: { FontAwesomeIcon },
    props: {
        links: {
            type: Object,
            default: () => ({}),
        },
    },
    computed: {
        link() {
            const links = Object.values(this.links || {});
            return links.length > 0 ? links[0] : null;
        },
    },
};
</script>
