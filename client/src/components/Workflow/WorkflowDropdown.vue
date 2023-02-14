<template>
    <div>
        <b-link
            v-b-tooltip.hover
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            :title="getWorkflowTooltip(sourceType, workflow)"
            aria-haspopup="true"
            aria-expanded="false">
            <font-awesome-icon icon="caret-down" />
            <span class="workflow-dropdown-name">{{ workflow.name }}</span>
            <span v-if="sourceType.includes('trs')">
                <font-awesome-icon icon="check" class="workflow-trs-icon" />
            </span>
            <span v-if="sourceType == 'url'">
                <font-awesome-icon class="workflow-external-link" icon="link" />
            </span>
        </b-link>
        <p v-if="workflow.description" class="workflow-dropdown-description">{{ workflow.description }}</p>
        <div class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                @keypress="$router.push(urlEdit)"
                @click.prevent="$router.push(urlEdit)">
                <span class="fa fa-edit fa-fw mr-1" />
                <span v-localize>Edit</span>
            </a>
            <a v-if="!isDeleted" class="dropdown-item" href="#" @click.prevent="onCopy">
                <span class="fa fa-copy fa-fw mr-1" />
                <span v-localize>Copy</span>
            </a>
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                @keypress="$router.push(urlInvocations)"
                @click.prevent="$router.push(urlInvocations)">
                <span class="fa fa-list fa-fw mr-1" />
                <span v-localize>Invocations</span>
            </a>
            <a v-if="!isDeleted" class="dropdown-item" :href="urlDownload">
                <span class="fa fa-download fa-fw mr-1" />
                <span v-localize>Download</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" href="#" @click.prevent="onRename">
                <span class="fa fa-signature fa-fw mr-1" />
                <span v-localize>Rename</span>
            </a>
            <a
                v-if="!readOnly && !isDeleted"
                class="dropdown-item"
                @keypress="$router.push(urlShare)"
                @click.prevent="$router.push(urlShare)">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span v-localize>Share</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" :href="urlExport">
                <span class="fa fa-file-export fa-fw mr-1" />
                <span v-localize>Export</span>
            </a>
            <a v-if="!isDeleted" class="dropdown-item" :href="urlView">
                <span class="fa fa-eye fa-fw mr-1" />
                <span v-localize>View</span>
            </a>
            <a v-if="sourceLabel && !isDeleted" class="dropdown-item" :href="sourceUrl">
                <span class="fa fa-globe fa-fw mr-1" />
                <span v-localize>{{ sourceLabel }}</span>
            </a>
            <a v-if="!readOnly && !isDeleted" class="dropdown-item" href="#" @click.prevent="onDelete">
                <span class="fa fa-trash fa-fw mr-1" />
                <span v-localize>Delete</span>
            </a>
            <a v-if="isDeleted" class="dropdown-item" href="#" @click.prevent="onRestore">
                <span class="fa fa-trash fa-fw mr-1" />
                <span v-localize>Restore</span>
            </a>
        </div>
    </div>
</template>
<script>
import { Services } from "./services";
import { withPrefix } from "utils/redirect";

import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown);

export default {
    components: {
        FontAwesomeIcon,
    },
    props: ["workflow"],
    computed: {
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
                tooltip = `Imported from TRS ID (version ${workflow.source_metadata.trs_version_id})`;
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
