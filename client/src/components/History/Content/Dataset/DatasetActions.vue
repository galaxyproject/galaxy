<template>
    <div class="dataset-actions mb-1">
        <div class="clearfix">
            <div class="btn-group float-left">
                <b-button
                    v-if="showError"
                    class="px-1"
                    title="Error"
                    size="sm"
                    variant="link"
                    :href="reportErrorUrl"
                    @click.prevent.stop="onError">
                    <span class="fa fa-bug" />
                </b-button>
                <dataset-download v-if="showDownloads" :item="item" @on-download="onDownload" />
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
                    :href="showDetailsUrl"
                    @click.prevent.stop="onInfo">
                    <span class="fa fa-info-circle" />
                </b-button>
                <b-button
                    v-if="showRerun"
                    class="rerun-btn px-1"
                    title="Run Job Again"
                    size="sm"
                    variant="link"
                    :href="rerunUrl"
                    @click.prevent.stop="onRerun">
                    <span class="fa fa-redo" />
                </b-button>
                <b-button
                    v-if="showVisualizations"
                    class="px-1"
                    title="Visualize"
                    size="sm"
                    variant="link"
                    :href="visualizeUrl"
                    @click.prevent.stop="onVisualize">
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
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath, prependPath } from "utils/redirect.js";
import { downloadUrlMixin } from "./mixins.js";
import DatasetDownload from "./DatasetDownload";

export default {
    components: {
        DatasetDownload,
    },
    mixins: [legacyNavigationMixin, downloadUrlMixin],
    props: {
        item: { type: Object, required: true },
        showHighlight: { type: Boolean, default: false },
        itemUrls: { type: Object, required: true },
    },
    computed: {
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
        reportErrorUrl() {
            return prependPath(this.itemUrls.reportError);
        },
        showDetailsUrl() {
            return prependPath(this.itemUrls.showDetails);
        },
        rerunUrl() {
            return prependPath(this.itemUrls.rerun);
        },
        visualizeUrl() {
            return prependPath(this.itemUrls.visualize);
        },
    },
    methods: {
        onCopyLink() {
            const msg = this.localize("Link is copied to your clipboard");
            sendToClipboard(absPath(this.downloadUrl), msg);
        },
        onDownload(resource) {
            window.location.href = resource;
        },
        onError() {
            this.backboneRoute(this.itemUrls.reportError);
        },
        onInfo() {
            this.backboneRoute(this.itemUrls.showDetails);
        },
        onRerun() {
            this.backboneRoute(`root?job_id=${this.item.creating_job}`);
        },
        onVisualize() {
            const name = this.item.name || "";
            const title = `Visualization of ${name}`;
            const path = this.itemUrls.visualize;
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
