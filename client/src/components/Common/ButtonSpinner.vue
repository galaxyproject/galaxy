<template>
    <b-button
        v-if="wait"
        v-b-tooltip.hover.bottom
        disabled
        variant="info"
        title="Please Wait..."
        class="d-flex flex-nowrap align-items-center text-nowrap">
        <font-awesome-icon icon="spinner" class="mr-2" spin />{{ title }}
    </b-button>
    <b-button
        v-else
        v-b-tooltip.hover.bottom
        variant="primary"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        @click="$emit('onClick')">
        <font-awesome-icon icon="play" class="mr-2" />{{ title }}
    </b-button>
</template>
<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSpinner, faPlay } from "@fortawesome/free-solid-svg-icons";

library.add(faSpinner);
library.add(faPlay);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        title: {
            type: String,
            required: true,
        },
        wait: {
            type: Boolean,
            default: false,
        },
        tooltip: {
            type: String,
            default: null,
        },
    },
};
</script>
