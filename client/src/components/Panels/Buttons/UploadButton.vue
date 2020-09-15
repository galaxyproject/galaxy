<template>
    <div class="upload-button">
        <div class="progress">
            <div
                class="progress-bar progress-bar-notransition"
                :class="`progress-bar-${status}`"
                :style="{
                    width: `${percentage}%`,
                }"
            ></div>
            <a
                class="upload-button-link"
                id="tool-panel-upload-button"
                @click="showUploadDialog"
                href="javascript:void(0)"
                role="button"
                v-b-tooltip.hover
                aria-label="Download from URL or upload files from disk"
                title="Download from URL or upload files from disk"
            >
                <font-awesome-icon icon="upload" />
            </a>
        </div>
    </div>
</template>

<script>
import { VBTooltip } from "bootstrap-vue";
import { getGalaxyInstance } from "app"; // FIXME:

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
library.add(faUpload);

export default {
    name: "UploadButton",
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
            const Galaxy = getGalaxyInstance();
            e.preventDefault();
            Galaxy.upload.show();
        },
    },
    created() {
        const Galaxy = getGalaxyInstance();

        Galaxy.upload.model.on("change", () => {
            this.status = Galaxy.upload.model.attributes.status;
            this.percentage = Galaxy.upload.model.attributes.percentage;
        });
    },
};
</script>

<style scoped></style>
