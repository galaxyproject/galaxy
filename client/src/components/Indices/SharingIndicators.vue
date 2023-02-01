<template>
    <span>
        <span v-if="object.published" v-b-tooltip.hover :title="'Published' | localize">
            <font-awesome-icon
                icon="globe"
                class="sharing-indicator-published"
                @click="$emit('filter', 'is:published')" />
        </span>
        <span v-if="object.shared" v-b-tooltip.hover :title="'Shared' | localize">
            <font-awesome-icon
                icon="share-alt"
                class="sharing-indicator-shared"
                @click="$emit('filter', 'is:shared_with_me')" />
        </span>
    </span>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { VBTooltip } from "bootstrap-vue";

import { faShareAlt, faGlobe } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";
library.add(faGlobe, faShareAlt);

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
