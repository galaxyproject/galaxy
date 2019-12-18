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
                <div class="ui-form-composite-messages mb-4" ref="messages">
                    <b-alert v-if="hasUpgradeMessages" variant="warning" show>
                        Some tools in this workflow may have changed since it was last saved or some errors were found.
                        The workflow may still run, but any new options will have default values. Please review the
                        messages below to make a decision about whether the changes will affect your analysis.
                    </b-alert>
                    <b-alert v-if="hasStepVersionChanges" variant="warning" show>
                        Some tools are being executed with different versions compared to those available when this
                        workflow was last saved because the other versions are not or no longer available on this Galaxy
                        instance. To upgrade your workflow and dismiss this message simply edit the workflow and re-save
                        it.
                    </b-alert>
                </div>
                <div class="ui-form-composite-header" ref="header"></div>
                <div class="ui-form-composite-steps" ref="steps"></div>
            </div>
        </div>
    </div>
</template>

<script>
import _ from "underscore";
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
            loading: true,
            hasUpgradeMessages: false,
            hasStepVersionChanges: false
        };
    },
    created() {
        const url = `${getAppRoot()}api/workflows/${this.workflowId}/download?style=run`;
        axios
            .get(url)
            .then(response => {
                const runData = response.data;
                this.hasUpgradeMessages = runData.has_upgrade_messages;
                this.hasStepVersionChanges = runData.step_version_changes && runData.step_version_changes.length > 0;
                this.loading = false;
                this.$nextTick(() => {
                    const el = this.$refs["run"];
                    new ToolFormComposite.View(_.extend(runData, { el }));
                });
            })
            .catch(response => {
                this.error = errorMessageAsString(response);
            });
    }
};
</script>
