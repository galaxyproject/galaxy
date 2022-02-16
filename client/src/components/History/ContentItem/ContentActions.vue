<template>
    <div class="mb-1 clearfix">
        <div class="btn-group float-left">
            <b-button
                v-if="item.state == 'error'"
                class="px-1"
                title="Error"
                size="sm"
                variant="link"
                @click.stop="onError">
                <span class="fa fa-exclamation-triangle" />
            </b-button>
            <b-button
                v-if="showDownloads"
                class="px-1"
                title="Copy link"
                size="sm"
                variant="link"
                @click.stop="$emit('link', item)">
                <span class="fa fa-link" />
            </b-button>
            <b-button
                v-if="showDownloads"
                :href="downloadUrl"
                class="px-1"
                title="Download"
                size="sm"
                variant="link"
                @click.stop="$emit('save', item)">
                <span class="fa fa-save" />
            </b-button>
            <b-button
                v-if="item.rerunnable && item.creating_job && item.state != 'upload' && item.state != 'noPermission'"
                class="px-1"
                title="Run job again"
                size="sm"
                variant="link"
                @click.stop="onRerun">
                <span class="fa fa-play" />
            </b-button>
            <b-button
                v-if="item.rerunnable && item.creating_job && item.state != 'upload' && item.state != 'noPermission'"
                class="px-1"
                title="Run job again"
                size="sm"
                variant="link"
                @click.stop="onRerun">
                <span class="fa fa-play" />
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
            <b-dropdown-item
                v-if="item.creating_job"
                title="Tool Help"
                @click.stop="showToolHelp(item.creating_job)">
                <Icon icon="question" class="mr-1" />
                <span v-localize>Tool Help</span>
            </b-dropdown-item>
            <b-button
                v-if="item.state != 'noPermission'"
                class="px-1"
                title="Dataset details"
                size="sm"
                variant="link"
                @click.stop="$emit('info', item)">
                <span class="fa fa-info-circle" />
            </b-button>
            <b-button
                v-if="item.state != 'noPermission'"
                class="px-1"
                title="Help"
                size="sm"
                variant="link"
                @click.stop="$emit('help', item)">
                <span class="fa fa-question" />
            </b-button>
        </div>
        <div class="btn-group float-right">
            <b-button class="px-1" title="Edit tags" size="sm" variant="link" @click.stop="$emit('tags', item)">
                <span class="fa fa-tags" />
            </b-button>
            <b-button
                class="px-1"
                title="Edit annotation"
                size="sm"
                variant="link"
                @click.stop="$emit('annotation', item)">
                <span class="fa fa-comment" />
            </b-button>
        </div>
    </div>
</template>

<script>
import { copy as sendToClipboard } from "utils/clipboard";
import { absPath } from "utils/redirect";

export default {
    props: {
        item: { type: Object, required: true },
    },
    computed: {
        showDownloads() {
            if (this.item.purged || !this.item.file_size || !this.item.file_size == 0) {
                return false;
            }
            return ["ok", "failed_metadata", "error"].includes(this.item.state);
        },
        showVisualizations() {
            //&& hasViz && isIn(STATES.OK, STATES.FAILED_METADATA)
            return true;
        },
        downloadUrl() {
            return prependPath(`datasets/${this.item.id}/display?to_ext=${this.item.file_ext}`);
        },
    },
    methods: {
        onCopyLink() {
            const relPath = this.item.download_url;
            const msg = this.localize("Link is copied to your clipboard");
            sendToClipboard(absPath(relPath), msg);
        },
        onError() {
            /*@click.stop="
                backboneRoute('datasets/error', {
                    dataset_id: dataset.id,
                })
            ">*/
        },
        onRerun() {
            /*
            :href="prependPath(dataset.getUrl('rerun'))"
            backboneRoute('/', {
                job_id: dataset.creating_job,
            })*/
        },
        onVisualize() {
            /*const showDetailsUrl = `/datasets/${this.dataset.id}/details`;
            const redirectParams = {
                path: showDetailsUrl,
                title: "Dataset details",
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute("visualizations", {
                    dataset_id: this.dataset.id,
                });
            }*/
        },
    },
};
</script>
