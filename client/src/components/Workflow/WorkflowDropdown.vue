<template>
    <div>
        <b-link
            aria-expanded="false"
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            :data-workflow-dropdown="workflow.id"
            draggable
            @dragstart="onDragStart"
            @dragend="onDragEnd">
            <Icon icon="caret-down" class="fa-lg" />
            <span class="workflow-dropdown-name">{{ workflow.name }}</span>
            <span
                v-if="sourceType.includes('trs')"
                v-b-tooltip.hover
                aria-haspopup="true"
                :title="getWorkflowTooltip(sourceType, workflow)">
                <Icon fixed-width icon="check" class="mr-1 workflow-trs-icon" />
            </span>
            <span
                v-if="sourceType == 'url'"
                v-b-tooltip.hover
                aria-haspopup="true"
                :title="getWorkflowTooltip(sourceType, workflow)">
                <Icon fixed-width icon="link" class="mr-1 workflow-external-link" />
            </span>
        </b-link>
        <p v-if="workflow.description" class="workflow-dropdown-description">
            <TextSummary :description="workflow.description" :show-details.sync="showDetails" />
        </p>
        <div class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                href="#"
                @keypress="$router.push(urlEdit)"
                @click.prevent="$router.push(urlEdit)">
                <Icon fixed-width icon="edit" class="mr-1" />
                <span v-localize>Edit</span>
            </a>
            <a v-if="!isDeleted && !isAnonymous" class="dropdown-item" href="#" @click.prevent="onCopy">
                <Icon fixed-width icon="copy" class="mr-1" />
                <span v-localize>Copy</span>
            </a>
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                href="#"
                @keypress="$router.push(urlInvocations)"
                @click.prevent="$router.push(urlInvocations)">
                <Icon fixed-width icon="sitemap" class="fa-rotate-270 mr-1" />
                <span v-localize>Invocations</span>
            </a>
            <a v-if="!isDeleted" class="dropdown-item" :href="urlDownload">
                <Icon fixed-width icon="download" class="mr-1" />
                <span v-localize>Download</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" href="#" @click.prevent="onRename">
                <Icon fixed-width icon="signature" class="mr-1" />
                <span v-localize>Rename</span>
            </a>
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                href="#"
                @keypress="$router.push(urlShare)"
                @click.prevent="$router.push(urlShare)">
                <Icon fixed-width icon="share-alt" class="mr-1" />
                <span v-localize>Share</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" :href="urlExport">
                <Icon fixed-width icon="file-export" class="mr-1" />
                <span v-localize>Export</span>
            </a>
            <a v-if="!isDeleted" class="dropdown-item" :href="urlView">
                <Icon fixed-width icon="eye" class="mr-1" />
                <span v-localize>View</span>
            </a>
            <a v-if="sourceLabel && !isDeleted" class="dropdown-item" target="_blank" :href="sourceUrl">
                <Icon fixed-width icon="external-link-alt" class="mr-1" />
                <span v-localize>{{ sourceLabel }}</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" href="#" @click.prevent="onDelete">
                <Icon fixed-width icon="trash" class="mr-1" />
                <span v-localize>Delete</span>
            </a>
            <a v-if="isDeleted" class="dropdown-item" href="#" @click.prevent="onRestore">
                <Icon fixed-width icon="trash-restore" class="mr-1" />
                <span v-localize>Restore</span>
            </a>
        </div>
    </div>
</template>
<script>
import { Services } from "./services";
import { withPrefix } from "utils/redirect";
import TextSummary from "components/Common/TextSummary";
import { mapState } from "pinia";
import { useUserStore } from "@/stores/userStore";
import { setDrag, clearDrag } from "@/utils/setDrag.js";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown, faSignature, faTimes, faEdit } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown);
library.add(faSignature);
library.add(faTimes);
library.add(faEdit);

export default {
    components: {
        TextSummary,
    },
    props: {
        workflow: { type: Object, required: true },
        detailsShowing: { type: Boolean, default: false },
    },
    computed: {
        ...mapState(useUserStore, ["isAnonymous"]),
        showDetails: {
            get() {
                return this.detailsShowing;
            },
            set() {
                this.$emit("toggleDetails");
            },
        },
        urlEdit() {
            return `/workflows/edit?id=${this.workflow.id}`;
        },
        urlDownload() {
            return withPrefix(`/api/workflows/${this.workflow.id}/download?format=json-download`);
        },
        urlShare() {
            return `/workflows/sharing?id=${this.workflow.id}`;
        },
        urlExport() {
            return withPrefix(`/workflows/export?id=${this.workflow.id}`);
        },
        urlView() {
            return withPrefix(`/published/workflow?id=${this.workflow.id}`);
        },
        urlInvocations() {
            return `/workflows/${this.workflow.id}/invocations`;
        },
        urlViewShared() {
            return withPrefix(
                `/workflow/display_by_username_and_slug?username=${this.workflow.owner}&slug=${encodeURIComponent(
                    this.workflow.slug
                )}`
            );
        },
        readOnly() {
            return !!this.workflow.shared;
        },
        isDeleted() {
            return this.workflow.deleted;
        },
        sourceUrl() {
            if (this.workflow.source_metadata?.url) {
                return this.workflow.source_metadata.url;
            } else if (this.workflow.source_metadata?.trs_server) {
                if (this.workflow.source_metadata?.trs_server == "dockstore") {
                    return `https://dockstore.org/workflows${this.workflow.source_metadata.trs_tool_id.slice(9)}`;
                } else {
                    // TODO: add WorkflowHub
                    return null;
                }
            } else {
                return null;
            }
        },
        sourceLabel() {
            if (this.workflow.source_metadata?.url) {
                return "View external link";
            } else if (this.workflow.source_metadata?.trs_server == "dockstore") {
                return "View on Dockstore";
            } else {
                // TODO: add WorkflowHub
                return null;
            }
        },
        sourceType() {
            if (this.workflow.source_metadata?.url) {
                return "url";
            } else if (this.workflow.source_metadata?.trs_server) {
                return `trs_${this.workflow.source_metadata?.trs_server}`;
            } else {
                return "";
            }
        },
    },
    created() {
        this.services = new Services();
    },
    methods: {
        onCopy: function () {
            this.services
                .copyWorkflow(this.workflow)
                .then((newWorkflow) => {
                    this.$emit("onAdd", newWorkflow);
                    this.$emit(
                        "onSuccess",
                        `Successfully copied workflow '${this.workflow.name}' to '${newWorkflow.name}'.`
                    );
                })
                .catch((error) => {
                    this.$emit("onError", error);
                });
        },
        onDelete: function () {
            const id = this.workflow.id;
            this.services
                .deleteWorkflow(id)
                .then((message) => {
                    this.$emit("onRemove", id);
                    this.$emit("onSuccess", message);
                })
                .catch((error) => {
                    this.$emit("onError", error);
                });
        },
        onDragStart: function (evt) {
            setDrag(evt, this.workflow);
        },
        onDragEnd: function () {
            clearDrag();
        },
        onRename: function () {
            const id = this.workflow.id;
            const name = this.workflow.name;
            const newName = window.prompt(`Enter a new name for workflow '${name}'`, name);
            if (newName) {
                const data = { name: newName };
                this.services
                    .updateWorkflow(id, data)
                    .then(() => {
                        this.$emit("onUpdate", id, data);
                        this.$emit("onSuccess", `Successfully changed name of workflow '${name}' to '${newName}'.`);
                    })
                    .catch((error) => {
                        this.$emit("onError", error);
                    });
            }
        },
        onRestore: function () {
            const id = this.workflow.id;
            this.services
                .undeleteWorkflow(id)
                .then((message) => {
                    this.$emit("onRestore", id);
                    this.$emit("onSuccess", message);
                })
                .catch((error) => {
                    this.$emit("onError", error);
                });
        },
        getWorkflowTooltip: function (sourceType, workflow) {
            let tooltip = "";
            if (sourceType.includes("trs")) {
                tooltip = `Imported from TRS ID (version: ${workflow.source_metadata.trs_version_id})`;
            } else if (sourceType == "url") {
                tooltip = `Imported from ${workflow.source_metadata.url}`;
            }
            return tooltip;
        },
    },
};
</script>

<style scoped>
.workflow-trs-icon {
    color: green;
}
</style>
