<template>
    <div>
        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters">
            <template v-slot:body>
                <Form :inputs="wpInputsArray" />
            </template>
        </FormCard>
        <FormCard title="History Options">
            <template v-slot:body>
                <Form :inputs="historyInputs" />
            </template>
        </FormCard>
        <div ref="form" />
    </div>
</template>

<script>
import ToolFormComposite from "mvc/tool/tool-form-composite";
import Form from "components/Form/Form";
import FormCard from "components/Form/FormCard";

export default {
    components: {
        Form,
        FormCard,
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
        wpInputsAvailable() {
            return this.wpInputsArray.length > 0;
        },
        wpInputsArray() {
            return Object.keys(this.model.wpInputs).map((k) => this.model.wpInputs[k]);
        },
    },
    mounted() {
        this.$nextTick(() => {
            const el = this.$refs["form"];
            const formProps = {
                el,
                model: this.model,
                setRunButtonStatus: this.setRunButtonStatus,
                handleInvocations: this.handleInvocations,
            };
            this.runForm = new ToolFormComposite.View(formProps);
        });
    },
    methods: {
        execute() {
            this.runForm.execute();
        },
        handleInvocations(invocations) {
            this.$emit("submissionSuccess", invocations);
        },
    },
};
</script>
