<template>
    <b-button
        id="tool-panel-upload-button"
        @click="showUploadDialog"
        v-b-tooltip.hover
        aria-label="Download from URL or upload files from disk"
        title="Download from URL or upload files from disk"
        class="upload-button"
        size="sm"
    >
        <div class="progress">
            <div
                class="progress-bar progress-bar-notransition"
                :class="`progress-bar-${status}`"
                :style="{
                    width: `${percentage}%`,
                }"
            />
        </div>
        <span class="position-relative">
            <font-awesome-icon icon="upload" class="mr-1" />
            <b>Upload Data</b>
        </span>
    </b-button>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
library.add(faUpload);

export default {
    components: { FontAwesomeIcon },
    directives: {
        "v-b-tooltip": VBTooltip,
    },
    data() {
        return {
            status: "",
            percentage: 0,
        };
    },
    methods: {
        showUploadDialog(e) {
            this.eventHub.$emit("upload:show");
        },
    },
    async created() {
        this.eventHub.$on("upload:status", (val) => {
            this.status = val;
        });
        this.eventHub.$on("upload:percentage", (val) => {
            this.percentage = Math.round(val);
        });
    },
};
</script>
