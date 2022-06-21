<template>
    <div class="dataset-actions mb-1">
        <div class="clearfix">
            <div class="btn-group float-left">
                <b-button v-if="showError" class="px-1" title="Error" size="sm" variant="link" @click.stop="onError">
                    <span class="fa fa-bug" />
                </b-button>
                <b-button
                    v-if="showDownloads && !metaFiles"
                    class="download-btn px-1"
                    title="Download"
                    size="sm"
                    variant="link"
                    @click.stop="onDownload">
                    <span class="fa fa-save" />
                </b-button>
                <b-dropdown
                    v-if="showDownloads && metaFiles"
                    no-caret
                    v-b-tooltip.bottom.hover
                    size="sm"
                    variant="link"
                    toggle-class="text-decoration-none"
                    title="Download"
                    data-description="dataset download">
                    <template v-slot:button-content>
                        <span class="fa fa-save"/>
                    </template>
                    <b-dropdown-item>
                        You have data.
                    </b-dropdown-item>
                </b-dropdown>
                <b-button
                    v-if="showDownloads"
                    class="px-1"
                    title="Copy Link"
                    size="sm"
                    variant="link"
                    @click.stop="onCopyLink">
                    <span class="fa fa-link" />
                </b-button>
                <b-button
                    v-if="showInfo"
                    class="params-btn px-1"
                    title="Dataset Details"
                    size="sm"
                    variant="link"
                    @click.stop="onInfo">
                    <span class="fa fa-info-circle" />
                </b-button>
                <b-button
                    v-if="showRerun"
                    class="rerun-btn px-1"
                    title="Run Job Again"
                    size="sm"
                    variant="link"
                    @click.stop="onRerun">
                    <span class="fa fa-redo" />
                </b-button>
                <b-button
                    v-if="showVisualizations"
                    class="px-1"
                    title="Visualize"
                    size="sm"
                    variant="link"
                    @click.stop="onVisualize">
                    <span class="fa fa-bar-chart-o" />
                </b-button>
                <b-button
                    v-if="showHighlight"
                    class="px-1"
                    title="Show Inputs for this item"
                    size="sm"
                    variant="link"
                    @click.stop="onHighlight">
                    <span class="fa fa-sitemap" />
                </b-button>
                <b-button v-if="showRerun" class="px-1" title="Help" size="sm" variant="link" @click.stop="onRerun">
                    <span class="fa fa-question" />
                </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { prependPath } from "utils/redirect";
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath } from "utils/redirect";

export default {
    mixins: [legacyNavigationMixin],
    props: {
        item: { type: Object, required: true },
        showHighlight: { type: Boolean, default: false },
    },
    computed: {
        downloadUrl() {
            return prependPath(`api/datasets/${this.item.id}/display?to_ext=${this.item.extension}`);
        },
        metaFiles() {
            return this.meta_files;
        },
        showDownloads() {
            return !this.item.purged && ["ok", "failed_metadata", "error"].includes(this.item.state);
        },
        showError() {
            return this.item.state == "error";
        },
        showInfo() {
            return this.item.state != "noPermission";
        },
        showRerun() {
            return (
                this.item.rerunnable &&
                this.item.creating_job &&
                this.item.state != "upload" &&
                this.item.state != "noPermission"
            );
        },
        showVisualizations() {
            // TODO: Check hasViz, if visualizations are activated in the config
            return !this.item.purged && ["ok", "failed_metadata", "error"].includes(this.item.state);
        },
    },
    methods: {
        onCopyLink() {
            const msg = this.localize("Link is copied to your clipboard");
            sendToClipboard(absPath(this.downloadUrl), msg);
        },
        onDownload() {
            window.location.href = this.downloadUrl;
        },
        onError() {
            this.backboneRoute("datasets/error", { dataset_id: this.item.id });
        },
        onInfo() {
            this.backboneRoute(`datasets/${this.item.id}/details`);
        },
        onRerun() {
            this.backboneRoute(`root?job_id=${this.item.creating_job}`);
        },
        onVisualize() {
            const name = this.item.name || "";
            const title = `Visualization of ${name}`;
            const path = `visualizations?dataset_id=${this.item.id}`;
            const redirectParams = {
                path: path,
                title: title,
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute(path);
            }
        },
        onHighlight() {
            this.$emit("toggleHighlights");
        },
    },
};
</script>
