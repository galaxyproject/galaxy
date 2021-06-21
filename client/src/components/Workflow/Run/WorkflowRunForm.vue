<template>
    <div>
        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters">
            <template v-slot:body>
                <Form :inputs="wpInputs" @onChange="onWpInputs" />
            </template>
        </FormCard>
        <FormCard title="History Options">
            <template v-slot:body>
                <Form :inputs="historyInputs" />
            </template>
        </FormCard>
        <FormCard v-if="cacheInputsAvailable" title="Job re-use Options">
            <template v-slot:body>
                <Form :inputs="cacheInputs" />
            </template>
        </FormCard>
        <FormCard v-if="resourceInputsAvailable" title="Workflow Resource Options">
            <template v-slot:body>
                <Form :inputs="resourceInputs" />
            </template>
        </FormCard>
        <div v-for="step in model.steps">
            <WorkflowRunToolStep v-if="step.step_type == 'tool'" :model="step" :placeholderParams="wpData" />
            <WorkflowRunDefaultStep v-else :model="step" />
        </div>
    </div>
</template>

<script>
import { getGalaxyInstance } from "app";
import Form from "components/Form/Form";
import FormCard from "components/Form/FormCard";
import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep";
import WorkflowRunToolStep from "./WorkflowRunToolStep";

export default {
    components: {
        Form,
        FormCard,
        WorkflowRunDefaultStep,
        WorkflowRunToolStep,
    },
    props: {
        model: {
            type: Object,
            required: true,
        },
        setRunButtonStatus: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            wpData: {},
            historyInputs: [
                {
                    type: "conditional",
                    name: "new_history",
                    test_param: {
                        name: "check",
                        label: "Send results to a new history",
                        type: "boolean",
                        value: "false",
                        help: "",
                    },
                    cases: [
                        {
                            value: "true",
                            inputs: [
                                {
                                    name: "name",
                                    label: "History name",
                                    type: "text",
                                    value: this.model.name,
                                },
                            ],
                        },
                    ],
                },
            ],
        };
    },
    computed: {
        cacheInputsAvailable() {
            const Galaxy = getGalaxyInstance();
            var extra_user_preferences = {};
            if (Galaxy.user.attributes.preferences && "extra_user_preferences" in Galaxy.user.attributes.preferences) {
                extra_user_preferences = JSON.parse(Galaxy.user.attributes.preferences.extra_user_preferences);
            }
            return;
            "use_cached_job|use_cached_job_checkbox" in extra_user_preferences
                ? extra_user_preferences["use_cached_job|use_cached_job_checkbox"] === "true"
                : false;
        },
        cacheInputs() {
            return [
                {
                    type: "conditional",
                    name: "use_cached_job",
                    test_param: {
                        name: "check",
                        label: "Attempt to reuse jobs with identical parameters?",
                        type: "boolean",
                        value: "false",
                        help: "This may skip executing jobs that you have already run.",
                    },
                },
            ];
        },
        resourceInputsAvailable() {
            return this.resourceInputs.length > 0;
        },
        resourceInputs() {
            return this.toArray(this.model.workflowResourceParameters);
        },
        wpInputsAvailable() {
            return this.wpInputs.length > 0;
        },
        wpInputs() {
            return this.toArray(this.model.wpInputs);
        },
    },
    methods: {
        onWpInputs(data) {
            this.wpData = data;
        },
        execute() {
            this.runForm.execute();
        },
        handleInvocations(invocations) {
            this.$emit("submissionSuccess", invocations);
        },
        toArray(obj) {
            return obj ? Object.keys(obj).map((k) => obj[k]) : [];
        },
    },
};
</script>
