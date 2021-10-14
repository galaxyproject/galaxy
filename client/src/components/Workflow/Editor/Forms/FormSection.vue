<template>
    <div :id="id" v-if="firstOutput">
        <FormElement
            :id="emailActionId"
            :value="emailActionValue"
            :payload="emailActionPayload"
            :ignore="false"
            title="Email notification"
            type="boolean"
            help="An email notification will be sent when the job has completed."
            @change="onChange"
        />
        <FormElement
            :id="deleteActionId"
            :value="deleteActionValue"
            :ignore="false"
            title="Output cleanup"
            type="boolean"
            help="Upon completion of this step, delete non-starred outputs from completed workflow steps if they are no longer required as inputs."
            @change="onChange"
        />
        <FormOutput v-for="(output, index) in outputs"
            :key="index"
            :output="output"
            :get-node="getNode"
            :datatypes="datatypes"
        />
    </div>
</template>

<script>
import FormElement from "components/Form/FormElement";
import FormOutput from "./FormOutput";

export default {
    components: {
        FormElement,
        FormOutput,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    computed: {
        node() {
            return this.getNode();
        },
        postJobActions() {
            return this.node.postJobActions;
        },
        outputs() {
            return this.node.outputs;
        },
        firstOutput() {
            return this.outputs.length > 0 && this.outputs[0];
        },
        emailActionId() {
            return `pja__${this.firstOutput.name}__EmailAction`;
        },
        emailActionValue() {
            return Boolean(this.postJobActions[`EmailAction${this.firstOutput.name}`]);
        },
        emailActionPayload() {
            return {
                host: window.location.host,
            };
        },
        deleteActionId() {
            return `pja__${this.firstOutput.name}__DeleteIntermediatesAction`;
        },
        deleteActionValue() {
            return Boolean(this.postJobActions[`DeleteIntermediatesAction${this.firstOutput.name}`]);
        },
    },
    methods: {
        onChange(values) {
            this.$emit("onChange", values);
        },
        /*onLabel(outputName, newLabel) {
            /*
            // TODO: Switch to revised data structure!
            const formVue = this.$refs["form"];
            if (formVue && formVue.form) {
                const form = formVue.form;
                form.data.create();
                const oldLabel = node.labelOutput(outputName, newLabel);
                const input_id = form.data.match(`__label__${outputName}`);
                const input_element = form.element_list[input_id];
                if (oldLabel) {
                    input_element.field.model.set("value", oldLabel);
                    input_element.model.set(
                        "error_text",
                        `Duplicate output label '${newLabel}' will be ignored.`
                    );
                } else {
                    input_element.model.set("error_text", "");
                }
                form.trigger("change");
            }
        },
        onChangeOutputDatatype(outputName, newDatatype) {
            this.$emit("onChangeOutputDatatype", outputName, newDatatype);
        },*/
    },
};
</script>
