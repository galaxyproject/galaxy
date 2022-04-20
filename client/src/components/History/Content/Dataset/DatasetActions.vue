<template>
    <div class="dataset-actions mb-1">
        <div class="clearfix">
            <div class="btn-group float-left">
                <b-button v-if="showError" class="px-1" title="Error" size="sm" variant="link" @click.stop="onError">
                    <span class="fa fa-bug" />
                </b-button>
                <b-button
                    v-if="showDownloads"
                    class="download-btn px-1"
                    title="Download"
                    size="sm"
                    variant="link"
                    @click.stop="onDownload">
                    <span class="fa fa-save" />
                </b-button>
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
                <b-button v-if="showRerun" class="px-1" title="Help" size="sm" variant="link" @click.stop="onRerun">
                    <span class="fa fa-question" />
                </b-button>
            </div>
            <div class="btn-group float-right">
                <b-button
                    class="px-1"
                    title="Edit Tags"
                    size="sm"
                    variant="link"
                    :pressed="showTags"
                    @click="onToggleTags">
                    <span class="fa fa-tags" />
                </b-button>
            </div>
        </div>
        <div v-if="showTags" class="mb-2">
            <StatelessTags v-model="tags" class="tags" @input="onTags" />
        </div>
    </div>
</template>

<script>
import { StatelessTags } from "components/Tags";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import { prependPath } from "utils/redirect";
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath } from "utils/redirect";
import { updateContentFields } from "components/History/model/queries";

export default {
    components: {
        StatelessTags,
    },
    mixins: [legacyNavigationMixin],
    props: {
        item: { type: Object, required: true },
    },
    data() {
        return {
            showTags: false,
            tags: this.item.tags,
        };
    },
    computed: {
        downloadUrl() {
            return prependPath(`api/datasets/${this.item.id}/display?to_ext=${this.item.extension}`);
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
        onTags() {
            updateContentFields(this.item, { tags: this.tags });
        },
        onToggleTags() {
            this.showTags = !this.showTags;
        },
        onVisualize() {
            const path = `visualizations?dataset_id=${this.item.id}`;
            const redirectParams = {
                path: path,
                title: "Dataset details",
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute(path);
            }
        },
    },
};
</script>
