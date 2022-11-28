<template>
    <b-alert show>
        <h4 class="mb-1">
            <i class="fa fa-info-circle empty-message"></i>
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
import { useGlobalUploadModal } from "composables/globalUploadModal";

export default {
    props: {
        message: { type: String, default: "This history is empty." },
    },
    setup() {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        return { openGlobalUploadModal };
    },
    methods: {
        clickDataLink() {
            this.eventHub.$emit("openToolSection", "getext");
        },
    },
};
</script>
