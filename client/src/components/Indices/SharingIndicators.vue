<template>
    <span>
        <b-button
            v-if="object.published"
            v-b-tooltip.hover
            class="sharing-indicator-published"
            size="sm"
            variant="link"
            :title="'Find all published items' | localize"
            @click.prevent="$emit('filter', 'is:published')">
            <font-awesome-icon icon="globe" />
        </b-button>
        <b-button
            v-if="object.importable"
            v-b-tooltip.hover
            class="sharing-indicator-importable"
            size="sm"
            variant="link"
            :title="'Find all importable items' | localize"
            @click.prevent="$emit('filter', 'is:importable')">
            <font-awesome-icon icon="link" />
        </b-button>
        <b-button
            v-if="object.shared"
            v-b-tooltip.hover
            class="sharing-indicator-shared"
            size="sm"
            variant="link"
            :title="'Find all items shared with me' | localize"
            @click.prevent="$emit('filter', 'is:shared_with_me')">
            <font-awesome-icon icon="share-alt" />
        </b-button>
    </span>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faShareAlt, faGlobe, faLink } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faGlobe, faShareAlt, faLink);

export default {
    components: {
        FontAwesomeIcon,
    },
    directives: {
        VBTooltip,
    },
    props: {
        object: {
            type: Object,
            required: true,
        },
    },
};
</script>
