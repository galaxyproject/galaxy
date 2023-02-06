<template>
    <ToolCard
        v-if="hasData"
        :id="configForm.id"
        :version="configForm.version"
        :title="configForm.name"
        :description="configForm.description"
        :options="configForm"
        :message-text="messageText"
        :message-variant="messageVariant"
        @onChangeVersion="onChangeVersion"
        @onUpdateFavorites="onUpdateFavorites">
        <template v-slot:body>
            <FormElement
                id="__label"
                :value="label"
                title="Label"
                help="Add a step label."
                :error="uniqueErrorLabel"
                @input="onLabel" />
            <FormElement
                id="__annotation"
                :value="annotation"
                title="Step Annotation"
                :area="true"
                help="Add an annotation or notes to this step. Annotations are available when a workflow is viewed."
                @input="onAnnotation" />
            <FormConditional :step="step" v-on="$listeners" />
            <div class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Tool Parameters </Heading>
                <FormDisplay
                    :id="id"
                    :inputs="inputs"
                    :errors="errors"
                    text-enable="Set in Advance"
                    text-disable="Set at Runtime"
                    :workflow-building-mode="true"
                    @onChange="onChange" />
            </div>
            <div class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Additional Options </Heading>
                <FormSection
                    :id="stepId"
                    :node-inputs="stepInputs"
                    :node-outputs="stepOutputs"
                    :step="step"
                    :datatypes="datatypes"
                    :post-job-actions="postJobActions"
                    @onChange="onChangePostJobActions" />
            </div>
        </template>
    </ToolCard>
</template>

<script>
import FormDisplay from "@/components/Form/FormDisplay.vue";
import ToolCard from "@/components/Tool/ToolCard.vue";
import FormSection from "./FormSection.vue";
import FormElement from "@/components/Form/FormElement.vue";
import FormConditional from "./FormConditional.vue";
import Utils from "utils/utils";
import Heading from "@/components/Common/Heading.vue";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import { useUniqueLabelError } from "../composables/useUniqueLabelError";
import { useStepProps } from "../composables/useStepProps";
import { toRef } from "vue";

export default {
    components: {
        FormDisplay,
        ToolCard,
        FormElement,
        FormConditional,
        FormSection,
        Heading,
    },
    props: {
        step: {
            // type Step from @/stores/workflowStepStore
            type: Object,
            required: true,
        },
        datatypes: {
            type: Array,
            required: true,
        },
    },
    emits: ["onSetData", "onUpdateStep", "onChangePostJobActions", "onAnnotation", "onLabel"],
    setup(props, { emit }) {
        const { stepId, annotation, label, stepInputs, stepOutputs, configForm, postJobActions } = useStepProps(
            toRef(props, "step")
        );
        const stepStore = useWorkflowStepStore();
        const uniqueErrorLabel = useUniqueLabelError(stepStore, label);

        return {
            stepId,
            annotation,
            label,
            stepInputs,
            stepOutputs,
            configForm,
            postJobActions,
            uniqueErrorLabel,
        };
    },
    data() {
        return {
            mainValues: null,
            messageText: "",
            messageVariant: "success",
        };
    },
    computed: {
        id() {
            return `${this.stepId}:${this.configForm.id}`;
        },
        toolCardId() {
            return `${this.stepId}`;
        },
        hasData() {
            return !!this.configForm?.id;
        },
        inputs() {
            const inputs = this.configForm.inputs;
            Utils.deepeach(inputs, (input) => {
                if (input.type) {
                    if (["data", "data_collection"].indexOf(input.type) != -1) {
                        input.titleonly = true;
                        input.info = `Data input '${input.name}' (${Utils.textify(input.extensions)})`;
                        input.value = { __class__: "RuntimeValue" };
                    } else {
                        input.connectable = ["rules"].indexOf(input.type) == -1;
                        input.collapsible_value = {
                            __class__: "RuntimeValue",
                        };
                        input.is_workflow =
                            (input.options && input.options.length === 0) ||
                            ["integer", "float"].indexOf(input.type) != -1;
                    }
                }
            });
            Utils.deepeach(inputs, (input) => {
                if (input.type === "conditional") {
                    input.connectable = false;
                    input.test_param.collapsible_value = undefined;
                }
            });
            return inputs;
        },
        errors() {
            return this.configForm.errors;
        },
    },
    methods: {
        onAnnotation(newAnnotation) {
            this.$emit("onAnnotation", this.stepId, newAnnotation);
        },
        onLabel(newLabel) {
            this.$emit("onLabel", this.stepId, newLabel);
        },
        /**
         * Change event is triggered on component creation and input changes.
         * @param { Object } values contains flat key-value pairs `prefixed-name=value`
         */
        onChange(values) {
            const initialRequest = this.mainValues === null;
            this.mainValues = values;
            if (!initialRequest) {
                this.postChanges();
            }
        },
        onChangePostJobActions(postJobActions) {
            this.$emit("onChangePostJobActions", this.stepId, postJobActions);
        },
        onChangeVersion(newVersion) {
            this.messageText = `Now you are using '${this.configForm.name}' version ${newVersion}.`;
            this.postChanges(newVersion);
        },
        onUpdateFavorites(user, newFavorites) {
            user.preferences["favorites"] = newFavorites;
        },
        postChanges(newVersion) {
            const payload = Object.assign({}, this.mainValues);
            const options = this.configForm;
            let toolId = options.id;
            let toolVersion = options.version;
            if (newVersion) {
                toolId = toolId.replace(toolVersion, newVersion);
                toolVersion = newVersion;
            }
            this.$emit("onSetData", this.stepId, {
                tool_id: toolId,
                tool_version: toolVersion,
                type: "tool",
                inputs: payload,
            });
        },
    },
};
</script>
