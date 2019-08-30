<template>
    <div>
        <b-link
            id="dropdownWorkflowDetails"
            class="font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false"
        >
            <span :class="icon" />
            {{ workflow.name }}
        </b-link>
        <div class="dropdown-menu" aria-labelledby="dropdownWorkflowDetails">
            <a
                v-for="ops in operations"
                :key="ops.label"
                class="dropdown-item"
                @click="onClick(ops.event)"
                :href="ops.url"
            >
                {{ ops.label }}
            </a>
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
            ownerOperations: [
                {
                    label: "Edit",
                    url: `${getAppRoot()}workflow/editor?id=${this.workflow.id}`
                },
                {
                    label: "Copy",
                    url: "#",
                    event: "copy"
                },
                {
                    label: "Download",
                    url: `${getAppRoot()}api/workflows/${this.workflow.id}/download?format=json-download`
                },
                {
                    label: "Rename",
                    url: "#",
                    event: "rename"
                },
                {
                    label: "Share",
                    url: `${getAppRoot()}workflow/sharing?id=${this.workflow.id}`
                },
                {
                    label: "View",
                    url: `${getAppRoot()}workflow/display_by_id?id=${this.workflow.id}`
                },
                {
                    label: "Delete",
                    url: "#",
                    event: "delete"
                }
            ],
            limitedOperations: [
                {
                    label: "Copy",
                    url: "#",
                    event: "copy"
                },
                {
                    label: "View",
                    url: `${getAppRoot()}workflow/display_by_username_and_slug?username=${this.workflow.owner}&slug=${
                        this.workflow.slug
                    }`
                }
            ]
        };
    },
    computed: {
        operations() {
            if (this.workflow.shared) {
                return this.limitedOperations;
            }
            return this.ownerOperations;
        },
        icon() {
            if (this.workflow.shared) {
                return "fa fa-retweet";
            }
            return null;
        }
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
    },
    methods: {
        onClick: function(event) {
            switch (event) {
                case "copy":
                    this.onCopy();
                    break;
                case "delete":
                    this.onDelete();
                    break;
                case "rename":
                    this.onRename();
                    break;
            }
        },
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
