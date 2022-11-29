<template>
    <b-alert show>
        <h4 class="mb-1">
            <FontAwesomeIcon icon="fa-info-circle" class="empty-message" />
            <span>{{ message | l }}</span>
        </h4>
        <p>
            <a v-localize href="#" @click.prevent="openGlobalUploadModal">You can load your own data</a>
            <span v-localize>or</span>
            <a v-localize href="#" @click.prevent="clickDataLink">get data from an external source</a>.
        </p>
    </b-alert>
</template>

<script>
import { openGlobalUploadModal } from "components/Upload";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";

library.add(faInfoCircle);

export default {
    components: { FontAwesomeIcon },
    props: {
        message: { type: String, default: "This history is empty." },
    },
    methods: {
        openGlobalUploadModal,
        clickDataLink() {
            this.eventHub.$emit("openToolSection", "getext");
        },
    },
};
</script>
