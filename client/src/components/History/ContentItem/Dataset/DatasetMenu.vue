<template>
    <PriorityMenu :starting-height="27">
        <PriorityMenuItem
            v-if="notIn(STATES.NOT_VIEWABLE, STATES.DISCARDED)"
            key="view-dataset"
            :title="displayButtonTitle"
            :disabled="dataset.purged || isIn(STATES.UPLOAD, STATES.NEW)"
            @click.stop="viewData"
            icon="fas fa-eye"
        />

        <PriorityMenuItem
            v-if="notIn(STATES.DISCARDED)"
            key="edit-dataset"
            :title="editButtonTitle"
            :disabled="dataset.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
            @click.stop="
                backboneRoute('datasets/edit', {
                    dataset_id: dataset.id,
                })
            "
            icon="fa fa-pencil"
        />

        <PriorityMenuItem
            v-if="dataset.accessible"
            key="delete-dataset"
            :title="deleteButtonTitle"
            :disabled="dataset.purged"
            @click.stop="onDeleteClick"
            :icon="dataset.deleted ? 'fas fa-trash-restore' : 'fas fa-trash'"
        />

        <PriorityMenuItem
            v-if="expanded"
            key="edit-tags"
            title="Edit History Tags"
            :pressed="showTags"
            @click.stop="$emit('update:showTags', !showTags)"
            icon="fas fa-tags"
        />

        <PriorityMenuItem
            v-if="isIn(STATES.ERROR)"
            key="show-error"
            title="Error"
            @click.stop="
                backboneRoute('datasets/error', {
                    dataset_id: dataset.id,
                })
            "
            icon="fa fa-bug"
        />

        <PriorityMenuItem
            v-if="!(showDownloads && dataset.hasMetaData)"
            key="download"
            title="Download"
            :href="prependPath(dataset.getUrl('download'))"
            target="_blank"
            download
            icon="fas fa-file-download"
        />

        <PriorityMenuItem
            v-if="showDownloads && dataset.hasMetaData"
            key="download-metadata"
            title="Download"
            :href="prependPath(dataset.getUrl('download'))"
            target="_blank"
            download
            icon="fas fa-file-download"
        />

        <div v-if="showDownloads && dataset.hasMetaData">
            <PriorityMenuItem
                v-for="mf in dataset.meta_files"
                :key="'download-' + mf.download_url"
                :title="'Download ' + mf.file_type"
                :href="prependPath(dataset.getUrl('meta_download') + mf.file_type)"
                target="_blank"
                download
                icon="fas fa-file-download"
            />
        </div>

        <PriorityMenuItem
            v-if="dataset.rerunnable && dataset.creating_job && notIn(STATES.UPLOAD, STATES.NOT_VIEWABLE)"
            key="run-job"
            title="Run job again"
            :href="prependPath(dataset.getUrl('rerun'))"
            @click.stop="
                backboneRoute('/', {
                    job_id: dataset.creating_job,
                })
            "
            icon="fa fa-refresh"
        />

        <PriorityMenuItem
            v-if="showViz && hasViz && isIn(STATES.OK, STATES.FAILED_METADATA)"
            key="visualize"
            title="Visualize Data"
            @click.stop.prevent="visualize"
            icon="fa-bar-chart"
        />

        <PriorityMenuItem
            v-if="currentUser && currentUser.id && dataset.creating_job"
            key="tool-tip"
            title="Tool Help"
            @click.stop="showToolHelp(dataset.creating_job)"
            icon="fa fa-question"
        />

        <PriorityMenuItem
            v-if="notIn(STATES.NOT_VIEWABLE)"
            key="dataset-details"
            title="View Details"
            @click.stop.prevent="
                iframeAdd({
                    path: dataset.getUrl('show_params'),
                    title: 'Dataset details',
                })
            "
            icon="fa fa-info-circle"
        />
    </PriorityMenu>
</template>

<script>
import { mapGetters } from "vuex";
import { Dataset } from "../../model";
import { PriorityMenu, PriorityMenuItem } from "components/PriorityMenu";
import { legacyNavigationMixin } from "components/plugins";

export default {
    inject: ["STATES"],
    mixins: [legacyNavigationMixin],

    components: {
        PriorityMenu,
        PriorityMenuItem,
    },

    props: {
        dataset: { type: Dataset, required: true },
        expanded: { type: Boolean, required: true },
        showTags: { type: Boolean, required: false, default: false },
    },

    data() {
        return {
            toolHelp: null,
            testVal: false,
        };
    },

    computed: {
        ...mapGetters("user", ["currentUser"]),
        ...mapGetters("config", ["config"]),

        showViz() {
            return this.config.visualizations_visible;
        },

        displayButtonTitle() {
            if (this.dataset.purged) {
                return "Cannot display datasets removed from disk";
            }
            if (this.dataset.state == this.STATES.UPLOAD) {
                return "This dataset must finish uploading before it can be viewed";
            }
            if (this.dataset.state == this.STATES.NEW) {
                return "This dataset is not yet viewable";
            }
            return "View data";
        },

        editButtonTitle() {
            if (this.dataset.deleted) {
                return "Undelete dataset to edit attributes";
            }
            if (this.dataset.purged) {
                return "Cannot edit attributes of datasets removed from disk";
            }
            const unreadyStates = new Set([this.STATES.UPLOAD, this.STATES.NEW]);
            if (unreadyStates.has(this.dataset.state)) {
                return "This dataset is not yet editable";
            }
            return "Edit attributes";
        },

        deleteButtonTitle() {
            return this.dataset.purged
                ? "Dataset has been permanently deleted"
                : this.dataset.deleted
                ? "Undelete"
                : "Delete";
        },

        showDownloads() {
            if (this.dataset.purged) {
                return false;
            }
            if (!this.dataset.hasData) {
                return false;
            }
            const okStates = new Set([this.STATES.OK, this.STATES.FAILED_METADATA, this.STATES.ERROR]);
            return okStates.has(this.dataset.state);
        },

        hasViz() {
            const viz_count = this.dataset.viz_count || 0;
            return viz_count && this.dataset.hasData && !this.dataset.deleted;
        },
    },

    methods: {
        notIn(...states) {
            const badStates = new Set(states);
            return !badStates.has(this.dataset.state);
        },

        isIn(...states) {
            const goodStates = new Set(states);
            return goodStates.has(this.dataset.state);
        },

        viewData() {
            const id = this.dataset.id;
            if (!id) return;
            this.useGalaxy((Galaxy) => {
                if (Galaxy.frame && Galaxy.frame.active) {
                    Galaxy.frame.addDataset(id);
                } else {
                    const path = this.dataset.getUrl("display");
                    if (path) {
                        this.iframeRedirect(path);
                    }
                }
            });
        },

        // wierd iframe navigation
        visualize() {
            const redirectParams = {
                path: this.dataset.getUrl("show_params"),
                title: "Dataset details",
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute("visualizations", {
                    dataset_id: this.dataset.id,
                });
            }
        },

        showToolHelp(job_id) {
            this.eventHub.$emit("toggleToolHelp", job_id);
        },

        onDeleteClick() {
            const eventName = this.dataset.deleted ? "undeleteDataset" : "deleteDataset";
            // console.log("emitting", eventName, this.dataset);
            this.$emit(eventName, this.dataset);
        },
    },
};
</script>
