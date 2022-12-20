<template>
    <b-nav-item
        id="tool-panel-upload-button"
        v-b-tooltip.hover.right
        :aria-label="title | localize"
        :title="title | localize"
        class="upload-button"
        @click="showUploadDialog">
        <div class="progress px-1">
            <div
                class="progress-bar progress-bar-notransition rounded"
                :class="`progress-bar-${status}`"
                :style="{
                    width: `${percentage}%`,
                }" />
        </div>
        <span class="position-relative">
            <font-awesome-icon icon="upload" />
        </span>
    </b-nav-item>
</template>

<script>
import Query from "utils/query-string-parsing";
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { useGlobalUploadModal } from "composables/globalUploadModal";

library.add(faUpload);

export default {
    components: { FontAwesomeIcon },
    directives: {
        "v-b-tooltip": VBTooltip,
    },
    props: {
        title: { type: String, default: "Download from URL or upload files from disk" },
    },
    setup() {
        const { openGlobalUploadModal } = useGlobalUploadModal();
        return { openGlobalUploadModal };
    },
    data() {
        return {
            status: "",
            percentage: 0,
        };
    },
    mounted() {
        this.eventHub.$on("upload:status", this.setStatus);
        this.eventHub.$on("upload:percentage", this.setPercentage);
        if (Query.get("tool_id") == "upload1") {
            this.showUploadDialog();
        }
    },
    beforeDestroy() {
        this.eventHub.$off("upload:status", this.setStatus);
        this.eventHub.$off("upload:percentage", this.setPercentage);
    },
    methods: {
        showUploadDialog() {
            this.openGlobalUploadModal();
        },
        setStatus(val) {
            this.status = val;
        },
        setPercentage(val) {
            this.percentage = Math.round(val);
        },
    },
};
</script>
