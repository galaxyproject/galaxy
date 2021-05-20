<template>
    <CurrentUser v-slot="{ user }">
        <FormCardTool
            :id="node.config_form.id"
            :user="user"
            :version="node.config_form.version"
            :title="node.config_form.name"
            :description="node.config_form.description"
            :options="node.config_form"
            :message-text="messageText"
            :message-variant="messageVariant"
            @onChangeVersion="onChangeVersion"
            @onUpdateFavorites="onUpdateFavorites"
        >
            <template v-slot:body>
                <FormElement
                    id="__label"
                    :value="node.label"
                    title="Label"
                    help="Add a step label."
                    @onChange="onLabel"
                    :error="errorLabel"
                />
                <FormElement
                    id="__annotation"
                    :value="node.annotation"
                    title="Step Annotation"
                    :area="true"
                    help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                    @onChange="onAnnotation"
                />
                <Form
                    :id="id"
                    :inputs="inputs"
                    :initial-errors="true"
                    text-enable="Set in Advance"
                    text-disable="Set at Runtime"
                    @onChange="onChange"
                    ref="form"
                />
                <FormSection
                    :id="id"
                    :get-node="getNode"
                    :datatypes="datatypes"
                    @onChange="onChangeSection"
                    @onChangeOutputDatatype="onChangeOutputDatatype"
                />
            </template>
        </FormCardTool>
    </CurrentUser>
</template>

<script>
import CurrentUser from "components/providers/CurrentUser";
import Form from "components/Form/Form";
import FormCardTool from "components/Form/FormCardTool";
import FormSection from "./FormSection";
import FormElement from "components/Form/FormElement";
import { getModule } from "components/Workflow/Editor/modules/services";
import { checkLabels } from "components/Workflow/Editor/modules/utilities";
import Utils from "utils/utils";

export default {
    components: {
        CurrentUser,
        Form,
        FormCardTool,
        FormElement,
        FormSection,
    },
    props: {
        datatypes: {
            type: Array,
            required: true,
        },
        getManager: {
            type: Function,
            required: true,
        },
        getNode: {
            type: Function,
            required: true,
        },
    },
    data() {
        return {
            mainValues: {},
            sectionValues: {},
            messageVariant: "",
            messageText: "",
        };
    },
    computed: {
        node() {
            return this.getNode();
        },
        workflow() {
            return this.getManager();
        },
        id() {
            return `${this.node.id}:${this.node.config_form.id}`;
        },
        errorLabel() {
            return checkLabels(this.node.id, this.node.label, this.workflow.nodes);
        },
        inputs() {
            const inputs = this.node.config_form.inputs;
            Utils.deepeach(inputs, (input) => {
                if (input.type) {
                    if (["data", "data_collection"].indexOf(input.type) != -1) {
                        input.hiddenInWorkflow = true;
                        input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                        input.value = { __class__: "RuntimeValue" };
                    } else if (input.type == "conditional") {
                        input.connectable = false;
                        input.test_param.collapsible_value = undefined;
                    } else if (!input.fixed) {
                        input.connectable = true;
                        input.collapsible_value = {
                            __class__: "RuntimeValue",
                        };
                        input.is_workflow =
                            (input.options && input.options.length === 0) ||
                            ["integer", "float"].indexOf(input.type) != -1;
                    }
                }
            });
            return inputs;
        },
    },
    methods: {
        onChangeOutputDatatype(outputName, newDatatype) {
            this.$emit("onChangeOutputDatatype", this.node.id, outputName, newDatatype);
        },
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.node.id, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.node.id, newLabel);
        },
        onChange(values) {
            this.mainValues = values;
            this.postChanges();
        },
        onChangeSection(values) {
            this.sectionValues = values;
            this.postChanges();
        },
        onChangeVersion(newVersion) {
            this.postChanges(newVersion);
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        postChanges(newVersion) {
            const options = this.node.config_form;
            getModule({
                tool_id: options.id,
                tool_version: newVersion || options.version,
                type: "tool",
                inputs: Object.assign({}, this.mainValues, this.sectionValues),
            }).then((data) => {
                this.$emit("onSetData", this.node.id, data);
                const form = this.$refs["form"];
                form.parseUpdate(data.config_form);
                form.parseErrors(data.config_form);
                if (newVersion) {
                    const options = data.config_form;
                    this.messageVariant = "success";
                    this.messageText = `Now you are using '${options.name}' version ${options.version}, id '${options.id}'.`;
                }
            });
        },
    },
};
</script>
