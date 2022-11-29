<template>
    <b-button
        v-if="offset > 200"
        v-b-tooltip.noninteractive.hover
        class="ui-btn-back-to-top btn-circle"
        title="Scroll To Top"
        variant="info"
        @click="$emit('click')">
        <FontAwesomeIcon icon="fa-arrow-up" />
    </b-button>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faArrowUp } from "@fortawesome/free-solid-svg-icons";

library.add(faArrowUp);

export default {
    components: { FontAwesomeIcon },
    props: {
        offset: {
            type: Number,
            default: 0,
        },
    },
};
</script>
