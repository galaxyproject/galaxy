<template>
    <div>
        <b-link
            id="workflow-dropdown"
            class="workflow-dropdown font-weight-bold"
            data-toggle="dropdown"
            aria-haspopup="true"
            aria-expanded="false">
            <font-awesome-icon icon="caret-down" />
            <span>{{ workflow.name }}</span>
        </b-link>
        <p v-if="workflow.description">{{ workflow.description }}</p>
        <div v-if="workflow.shared" class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a class="dropdown-item" href="#" @click.prevent="onCopy">
                <span class="fa fa-copy fa-fw mr-1" />
                <span>Copy</span>
            </a>
            <a class="dropdown-item" :href="urlViewShared">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>View</span>
            </a>
        </div>
        <div v-else class="dropdown-menu" aria-labelledby="workflow-dropdown">
            <a class="dropdown-item" :href="urlEdit">
                <span class="fa fa-edit fa-fw mr-1" />
                <span>Edit</span>
            </a>
            <a class="dropdown-item" href="#" @click.prevent="onCopy">
                <span class="fa fa-copy fa-fw mr-1" />
                <span>Copy</span>
            </a>
            <a class="dropdown-item" :href="urlDownload">
                <span class="fa fa-download fa-fw mr-1" />
                <span>Download</span>
            </a>
            <a class="dropdown-item" href="#" @click.prevent="onRename">
                <span class="fa fa-signature fa-fw mr-1" />
                <span>Rename</span>
            </a>
            <a class="dropdown-item" :href="urlShare">
                <span class="fa fa-share-alt fa-fw mr-1" />
                <span>Share</span>
            </a>
            <a class="dropdown-item" :href="urlView">
                <span class="fa fa-eye fa-fw mr-1" />
                <span>View</span>
            </a>
            <a class="dropdown-item" href="#" @click.prevent="onDelete">
                <span class="fa fa-trash fa-fw mr-1" />
                <span>Delete</span>
            </a>
        </div>
    </div>
</template>
<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faCaretDown } from "@fortawesome/free-solid-svg-icons";

library.add(faCaretDown);

export default {
    props: ["workflow"],
    components: {
        FontAwesomeIcon,
    },
    computed: {
        urlEdit() {
            return `${getAppRoot()}workflow/editor?id=${this.workflow.id}`;
        },
        urlDownload() {
            return `${getAppRoot()}api/workflows/${this.workflow.id}/download?format=json-download`;
        },
        urlShare() {
            return `${getAppRoot()}workflow/sharing?id=${this.workflow.id}`;
        },
        urlView() {
            return `${getAppRoot()}workflow/display_by_id?id=${this.workflow.id}`;
        },
        urlViewShared() {
            return `${getAppRoot()}workflow/display_by_username_and_slug?username=${this.workflow.owner}&slug=${
                this.workflow.slug
            }`;
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
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
            const name = this.workflow.name;
            if (window.confirm(`Are you sure you want to delete workflow '${name}'?`)) {
                this.services
                    .deleteWorkflow(id)
                    .then((message) => {
                        this.$emit("onRemove", id);
                        this.$emit("onSuccess", message);
                    })
                    .catch((error) => {
                        this.$emit("onError", error);
                    });
            }
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
    },
};
</script>
