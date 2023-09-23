<template>
    <b-button v-if="wait" disabled variant="info" class="d-flex flex-nowrap align-items-center text-nowrap">
        <FontAwesomeIcon icon="spinner" class="mr-2" spin />{{ title }}
    </b-button>
    <b-button
        v-else
        v-b-tooltip.hover.bottom="wait ? '' : tooltip"
        :disabled="disabled"
        variant="primary"
        class="d-flex flex-nowrap align-items-center text-nowrap"
        @click="$emit('onClick')">
        <FontAwesomeIcon :icon="icon" class="mr-2" />{{ title }}
    </b-button>
</template>
<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay, faSpinner, faStop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faSpinner);
library.add(faPlay);
library.add(faStop);

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
        icon: {
            type: String,
            default: "play",
        },
        disabled: {
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
