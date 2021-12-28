<template>
    <div>
        <b-button-group>
            <IconButton
                v-if="notIn(STATES.NOT_VIEWABLE, STATES.DISCARDED)"
                icon="eye"
                :title="displayButtonTitle"
                :disabled="dataset.purged || isIn(STATES.UPLOAD, STATES.NEW)"
                @click.stop="viewData"
                variant="link"
                class="px-1"
            />
            <IconButton
                v-if="writable && notIn(STATES.DISCARDED)"
                icon="pen"
                :title="editButtonTitle"
                :disabled="dataset.deleted || isIn(STATES.UPLOAD, STATES.NEW)"
                @click.stop="backboneRoute('datasets/edit', { dataset_id: dataset.id })"
                variant="link"
                class="px-1"
            />
            <IconButton
                v-if="writable && dataset.accessible"
                :icon="dataset.deleted ? 'trash-restore' : 'trash'"
                :title="deleteButtonTitle"
                :disabled="dataset.purged"
                v-b-modal="bsId('delete-modal')"
                variant="link"
                class="px-1"
                @click.stop
            />

            <b-dropdown
                right
                size="sm"
                variant="link"
                :text="'Dataset Operations' | l"
                toggle-class="p-1 pl-2"
                class="flex-grow-0"
                v-if="expanded"
                boundary="window"
            >
                <template v-slot:button-content>
                    <Icon icon="ellipsis-v" variant="link" />
                    <span class="sr-only">Dataset Operations</span>
                </template>

                <b-dropdown-item
                    v-if="isIn(STATES.ERROR)"
                    key="show-error"
                    title="Error"
                    @click.stop="
                        backboneRoute('datasets/error', {
                            dataset_id: dataset.id,
                        })
                    "
                >
                    <Icon icon="exclamation-triangle" class="mr-1" />
                    <span v-localize>Show Error</span>
                </b-dropdown-item>

                <b-dropdown-item
                    v-if="!dataset.purged && dataset.getUrl('download')"
                    title="Copy Link"
                    @click.stop="$emit('copy-link')"
                >
                    <Icon icon="link" class="mr-1" />
                    <span v-localize>Copy Link</span>
                </b-dropdown-item>

                <b-dropdown-item
                    v-if="!(showDownloads && dataset.hasMetaData)"
                    title="Download"
                    :href="prependPath(dataset.getUrl('download'))"
                    target="_blank"
                    download
                >
                    <Icon icon="download" class="mr-1" />
                    <span v-localize>Download</span>
                </b-dropdown-item>

                <b-dropdown-group v-if="showDownloads && dataset.hasMetaData">
                    <b-dropdown-item
                        v-for="mf in dataset.meta_files"
                        :key="'download-' + mf.download_url"
                        :title="'Download ' + mf.file_type"
                        :href="prependPath(dataset.getUrl('meta_download') + mf.file_type)"
                        target="_blank"
                        download
                    >
                        <Icon icon="download" class="mr-1" />
                        <span v-localize>{{ "Download " + mf.file_type }}</span>
                    </b-dropdown-item>
                </b-dropdown-group>

                <b-dropdown-item
                    v-if="dataset.rerunnable && dataset.creating_job && notIn(STATES.UPLOAD, STATES.NOT_VIEWABLE)"
                    title="Run job again"
                    :href="prependPath(dataset.getUrl('rerun'))"
                    @click.stop.prevent="
                        backboneRoute('/', {
                            job_id: dataset.creating_job,
                        })
                    "
                >
                    <Icon icon="play" class="mr-1" />
                    <span v-localize>Run job again</span>
                </b-dropdown-item>

                <b-dropdown-item
                    v-if="showViz && hasViz && isIn(STATES.OK, STATES.FAILED_METADATA)"
                    title="Visualize Data"
                    @click.stop.prevent="visualize"
                >
                    <Icon icon="chart-area" class="mr-1" />
                    <span v-localize>Visualize Data</span>
                </b-dropdown-item>

                <b-dropdown-item
                    v-if="currentUser && currentUser.id && dataset.creating_job"
                    title="Tool Help"
                    @click.stop="showToolHelp(dataset.creating_job)"
                >
                    <Icon icon="question" class="mr-1" />
                    <span v-localize>Tool Help</span>
                </b-dropdown-item>

                <b-dropdown-item
                    v-if="notIn(STATES.NOT_VIEWABLE)"
                    key="dataset-details"
                    title="View Dataset Details"
                    @click.stop.prevent="showDetails"
                >
                    <Icon icon="info-circle" class="mr-1" />
                    <span v-localize>View Dataset Details</span>
                </b-dropdown-item>
            </b-dropdown>
        </b-button-group>

        <!-- modals -->
        <b-modal :id="bsId('delete-modal')" title="Delete Dataset?" title-tag="h2" @ok="onDeleteClick">
            <p v-localize>Really delete this dataset?</p>
        </b-modal>
    </div>
</template>

<script>
import { mapGetters } from "vuex";
import { Dataset } from "../../model";
import { legacyNavigationMixin } from "components/plugins/legacyNavigation";
import IconButton from "components/IconButton";

export default {
    mixins: [legacyNavigationMixin],
    inject: ["STATES"],

    components: {
        IconButton,
    },

    props: {
        dataset: { type: Dataset, required: true },
        expanded: { type: Boolean, required: true },
        writable: { type: Boolean, default: true },
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
            if (!id) {
                return;
            }
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
            const showDetailsUrl = `/datasets/${this.dataset.id}/details`;
            const redirectParams = {
                path: showDetailsUrl,
                title: "Dataset details",
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute("visualizations", {
                    dataset_id: this.dataset.id,
                });
            }
        },

        showDetails() {
            const showDetailsUrl = `/datasets/${this.dataset.id}/details`;
            const redirectParams = {
                path: showDetailsUrl,
                title: "Dataset details",
                tryIframe: false,
            };
            if (!this.iframeAdd(redirectParams)) {
                this.backboneRoute(showDetailsUrl);
            }
        },

        showToolHelp(job_id) {
            this.eventHub.$emit("toggleToolHelp", job_id);
        },

        onDeleteClick() {
            const eventName = this.dataset.deleted ? "undelete" : "delete";
            this.$emit(eventName);
        },

        // bootstrap demands ids instead of simply using a ref so I guess we're doing this
        bsId(suffix) {
            return `dataset-${this.dataset.id}-${suffix}`;
        },
    },
};
</script>
