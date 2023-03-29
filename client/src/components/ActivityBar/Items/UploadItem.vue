<template>
    <ActivityItem
        id="tool-panel-upload-button"
        title="Upload"
        icon="upload"
        :tooltip="tooltip"
        @click="showUploadDialog">
        <template>
            <div class="upload-item-progress">
                <div
                    class="progress-bar progress-bar-notransition"
                    :class="`progress-bar-${status}`"
                    :style="{
                        width: `${percentage}%`,
                    }" />
            </div>
        </template>
    </ActivityItem>
</template>

<script>
import Query from "utils/query-string-parsing";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import ActivityItem from "components/ActivityBar/ActivityItem";

export default {
    components: { ActivityItem },
    props: {
        tooltip: { type: String, default: "Download from URL or upload files from disk" },
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
