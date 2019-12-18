<template>
    <div>
        <b-alert variant="error" show v-if="error">
            {{ error }}
        </b-alert>
        <b-alert v-if="loading" variant="info" show>
            <loading-span message="Loading workflow run data" />
        </b-alert>
        <div v-else>
            <div ref="run" class="ui-form-composite">
                <div class="ui-form-composite-messages mb-4" ref="messages"></div>
                <div class="ui-form-composite-header" ref="header"></div>
                <div class="ui-form-composite-steps" ref="steps"></div>
            </div>
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
                    const el = this.$refs["run"];
                    const view = new ToolFormComposite.View(_.extend(response.data, { el }));
                });
            })
            .catch(response => {
                this.error = errorMessageAsString(response);
            });
    }
};
</script>
