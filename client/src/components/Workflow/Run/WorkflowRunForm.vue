<template>
    <div>
        <FormCard v-if="wpInputsAvailable" title="Workflow Parameters" icon="">
            <template v-slot:body>
                <Form :inputs="wpInputsArray" :options="model" />
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
            runForm: null,
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
