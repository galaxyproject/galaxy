<template>
    <div>
        <b-link
            id="workflow-dropdown"
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
        >
            <span :class="icon" />
            {{ workflow.name }}
        </b-link>
        <p>{{ workflow.description }}</p>
        <div v-if="workflow.shared" class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a class="dropdown-item" href="#" @click="onCopy">Copy</a>
            <a class="dropdown-item" :href="urlViewShared">View</a>
        </div>
        <div v-else class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a class="dropdown-item" :href="urlEdit">Edit</a>
            <a class="dropdown-item" href="#" @click="onCopy">Copy</a>
            <a class="dropdown-item" :href="urlDownload">Download</a>
            <a class="dropdown-item" href="#" @click="onRename">Rename</a>
            <a class="dropdown-item" :href="urlShare">Share</a>
            <a class="dropdown-item" :href="urlView">View</a>
            <a class="dropdown-item" href="#" @click="onDelete">Delete</a>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services.js";
export default {
    props: ["workflow"],
    data() {
        return {
            urlEdit: `${getAppRoot()}workflow/editor?id=${this.workflow.id}`,
            urlDownload: `${getAppRoot()}api/workflows/${this.workflow.id}/download?format=json-download`,
            urlShare: `${getAppRoot()}workflow/sharing?id=${this.workflow.id}`,
            urlView: `${getAppRoot()}workflow/display_by_id?id=${this.workflow.id}`,
            urlViewShared: `${getAppRoot()}workflow/display_by_username_and_slug?username=${this.workflow.owner}&slug=${
                this.workflow.slug
            }`
        };
    },
    computed: {
        icon() {
            if (this.workflow.shared) {
                return "fa fa-share-alt";
            }
            return null;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
    },
    methods: {
        onCopy: function() {
            this.services
                .copyWorkflow(this.workflow)
                .then(newWorkflow => {
                    this.$emit("onAdd", newWorkflow);
                    this.$emit(
                        "onSuccess",
                        `Successfully copied workflow '${this.workflow.name}' to '${newWorkflow.name}'.`
                    );
                })
                .catch(error => {
                    this.$emit("onError", error);
                });
        },
        onDelete: function() {
            const id = this.workflow.id;
            const name = this.workflow.name;
            if (window.confirm(`Are you sure you want to delete workflow '${name}'?`)) {
                this.services
                    .deleteWorkflow(id)
                    .then(message => {
                        this.$emit("onRemove", id);
                        this.$emit("onSuccess", message);
                    })
                    .catch(error => {
                        this.$emit("onError", error);
                    });
            }
        },
        onRename: function() {
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
                    .catch(error => {
                        this.$emit("onError", error);
                    });
            }
        }
    }
};
</script>
