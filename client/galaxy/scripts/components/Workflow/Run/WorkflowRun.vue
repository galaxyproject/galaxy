<template>
    <div>
        <b-alert variant="error" show v-if="error">
            {{ error }}
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow run data" />
        </b-alert>
        <div v-else>
            <div class="workflow-run-form" ref="workflow-run-form" />
        </div>
    </div>
</template>

<script>
import axios from "axios";

import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload";
import ToolFormComposite from "mvc/tool/tool-form-composite";
import { errorMessageAsString } from "utils/simple-error";

export default {
    components: {
        LoadingSpan
    },
    props: {
        workflowId: { type: String }
    },
    data() {
        return {
            error: false,
            loading: true
        };
    },
    created() {
        const url = `${getAppRoot()}api/workflows/${this.workflowId}/download?style=run`;
        axios
            .get(url)
            .then(response => {
                this.loading = false;
                this.$nextTick(() => {
                    const formEl = this.$refs["workflow-run-form"];
                    console.log(this.$refs);
                    const view = new ToolFormComposite.View(_.extend(response.data, { el: formEl }));
                });
            })
            .catch(response => {
                this.error = errorMessageAsString(response);
            });
    }
};
</script>
