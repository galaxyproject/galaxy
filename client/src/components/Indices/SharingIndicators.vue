<template>
    <span>
        <b-button
            v-if="object.published"
            v-b-tooltip.hover
            class="sharing-indicator-published"
            size="sm"
            variant="link"
            :title="'Search more published workflows' | localize"
            @click.prevent="$emit('filter', 'is:published')">
            <Icon fixed-width icon="globe" />
        </b-button>
        <b-button
            v-if="object.shared"
            v-b-tooltip.hover
            class="sharing-indicator-shared"
            size="sm"
            variant="link"
            :title="'Search more workflows shared with me' | localize"
            @click.prevent="$emit('filter', 'is:shared_with_me')">
            <Icon fixed-width icon="share-alt" />
        </b-button>
    </span>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { faShareAlt, faGlobe } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faGlobe, faShareAlt);

export default {
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
