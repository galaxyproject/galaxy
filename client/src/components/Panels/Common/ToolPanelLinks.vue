<template>
    <span v-if="link">
        <a :href="link" target="_blank" style="display: inline">
            <font-awesome-icon v-show="show" v-b-tooltip.hover title="Link" icon="external-link-alt" />
        </a>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faExternalLinkAlt } from "@fortawesome/free-solid-svg-icons";

library.add(faExternalLinkAlt);

export default {
    components: { FontAwesomeIcon },
    props: {
        links: {
            type: Object,
        },
        show: {
            type: Boolean,
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
