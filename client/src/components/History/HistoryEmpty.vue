<template>
    <b-alert show>
        <h4>
            <i class="fa fa-info-circle"></i>
            <span v-localize>This history is empty.</span>
        </h4>
        <p>
            <a href="#" @click.prevent="openGlobalUploadModal" v-localize>You can load your own data</a> or
            <a href="#" @click.prevent="clickDataLink" v-localize>get data from an external source</a>.
        </p>
    </b-alert>
</template>

<script>
import { openGlobalUploadModal } from "components/Upload";

export default {
    methods: {
        openGlobalUploadModal,
        clickDataLink() {
            this.eventHub.$emit("openToolSection", "getext");
        },
    },
};
</script>
