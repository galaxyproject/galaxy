<template>
    <b-button
        v-if="wait"
        v-b-tooltip.hover.bottom
        disabled
        variant="info"
        title="Please Wait..."
        class="d-flex flex-nowrap align-items-center text-nowrap">
        <FontAwesomeIcon icon="spinner" class="mr-2" spin />{{ title }}
    </b-button>
    <b-button
        v-else
        v-b-tooltip.hover.bottom
        variant="primary"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        :title="tooltip"
        @click="$emit('onClick')">
        <FontAwesomeIcon icon="play" class="mr-2" />{{ title }}
    </b-button>
</template>
<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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
