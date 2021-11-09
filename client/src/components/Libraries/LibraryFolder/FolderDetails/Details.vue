<template>
    <div>
        <b-button title="Show location details" v-b-modal.details-modal>
            <font-awesome-icon icon="info-circle" /> Details
        </b-button>

        <b-modal id="details-modal"> my amazing details! </b-modal>
    </div>
</template>

<script>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";

library.add(faInfoCircle);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        metadata: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            someVariable: "example",
        };
    },
    methods: {},
};
</script>
