<template>
    <div>
        <div v-if="workflow">
            <h1 class="mb-4 h-lg">Workflow Export of `{{ workflow.name }}`</h1>
            <div v-if="workflow.importable && workflow.slug">
                <a :href="importUrl">{{ importUrl }}</a>
                <div>
                    <small>
                        Use this URL to import the workflows directly into another Galaxy server. You can copy it into
                        the input field titled when importing a workflow.
                    </small>
                </div>
                <hr />
            </div>
            <b-alert v-else variant="info" show>
                This workflow is not accessible. Please use the sharing option to "Make Workflow Accessible and Publish"
                to obtain a URL for importing to another Galaxy.
            </b-alert>
            <a :href="downloadUrl">Download Workflow</a>
            <div>
                <small class="text-muted">
                    Downloads a file which can be saved or imported into another Galaxy server.
                </small>
            </div>
            <hr />
            <a :href="svgUrl">Create Image</a>
            <div>
                <small class="text-muted"> Download an image of the workflow in SVG format. </small>
            </div>
        </div>
        <b-alert v-else-if="!!error" variant="danger" show>
            <span>
                {{ error }}. Click
                <router-link class="require-login-link" to="/login/start">here</router-link>
                to login.
            </span>
        </b-alert>
        <LoadingSpan v-else message="Loading workflow" />
    </div>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { withPrefix } from "utils/redirect";
import { urlData } from "utils/url";
import LoadingSpan from "components/LoadingSpan";
Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            error: null,
            workflow: null,
        };
    },
    computed: {
        downloadUrl() {
            return withPrefix(`/api/workflows/${this.workflow.id}/download?format=json-download`);
        },
        importUrl() {
            const location = window.location;
            const url = withPrefix(`/u/${this.workflow.owner}/w/${this.workflow.slug}/json`);
            return `${location.protocol}//${location.host}${url}`;
        },
        svgUrl() {
            return withPrefix(`/workflow/gen_image?id=${this.workflow.id}`);
        },
    },
    watch: {
        id() {
            this.getWorkflow();
        },
    },
    created() {
        this.getWorkflow();
    },
    methods: {
        getWorkflow() {
            const url = `/api/workflows/${this.id}`;
            urlData({ url })
                .then((workflow) => {
                    this.workflow = workflow;
                    this.error = null;
                })
                .catch((message) => {
                    this.error = message || "Loading workflow failed.";
                });
        },
    },
};
</script>
