import { visitInputs } from "components/Form/utilities";
import _ from "underscore";
import { isEmpty } from "utils/utils";

export class WorkflowRunModel {
    constructor(runData) {
        this.runData = runData;
        this.name = runData.name;
        this.workflowResourceParameters = runData.workflow_resource_parameters;
        this.hasWorkflowResourceParameters = !_.isEmpty(this.workflowResourceParameters);
        this.historyId = runData.history_id;
        this.workflowId = runData.id;

        this.hasUpgradeMessages = runData.has_upgrade_messages;
        this.hasStepVersionChanges = !_.isEmpty(runData.step_version_changes);

        this.steps = [];
        this.links = [];
        this.parms = [];
        this.wpInputs = {};
        this.parameterInputLabels = [];

        let hasOpenToolSteps = false;
        let hasReplacementParametersInToolForm = false;

        _.each(runData.steps, (step, i) => {
            const isParameterStep = step.step_type == "parameter_input";
            var title = `${parseInt(i + 1)}: ${step.step_label || step.step_name}`;
            if (step.annotation) {
                title += ` - ${step.annotation}`;
            }
            if (step.step_version) {
                title += ` (Galaxy 版本 ${step.step_version})`;
            }
            step = Object.assign(
                {
                    index: i,
                    fixed_title: _.escape(title),
                    expanded: i == 0 || isDataStep(step) || isParameterStep,
                    errors: step.messages,
                },
                step
            );
            this.steps[i] = step;
            this.links[i] = [];
            this.parms[i] = {};
            if (isParameterStep && step.step_label) {
                this.parameterInputLabels.push(step.step_label);
            }
        });

        // build linear index of step input pairs
        _.each(this.steps, (step, i) => {
            visitInputs(step.inputs, (input, name) => {
                this.parms[i][name] = input;
            });
        });

        // iterate through data input modules and collect linked sub steps
        _.each(this.steps, (step, i) => {
            _.each(step.output_connections, (output_connection) => {
                _.each(this.steps, (sub_step, j) => {
                    if (sub_step.step_index === output_connection.input_step_index) {
                        this.links[i].push(sub_step);
                    }
                });
            });
        });

        // convert all connected data inputs to hidden fields with proper labels,
        // and track the linked source step
        _.each(this.steps, (step, i) => {
            _.each(this.steps, (sub_step, j) => {
                var connections_by_name = {};
                _.each(step.output_connections, (connection) => {
                    if (sub_step.step_index === connection.input_step_index) {
                        connections_by_name[connection.input_name] = connection;
                    }
                });
                _.each(this.parms[j], (input, name) => {
                    var connection = connections_by_name[name];
                    if (connection) {
                        input.connected = true;
                        input.type = "hidden";
                        input.help = input.step_linked ? `${input.help}, ` : "";
                        input.help += `连接到 '${connection.output_name}' 从步骤 ${parseInt(i) + 1}`;
                        input.step_linked = input.step_linked || [];
                        input.step_linked.push({ index: step.index, step_type: step.step_type });
                    }
                });
            });
        });

        // identify and configure workflow parameters
        var wp_count = 0;

        const _ensureWorkflowParameter = (wp_name) => {
            return (this.wpInputs[wp_name] = this.wpInputs[wp_name] || {
                label: wp_name,
                name: wp_name,
                type: "text",
                color: `hsl( ${++wp_count * 100}, 70%, 30% )`,
                cls: "ui-input-linked",
                links: [],
                optional: true,
            });
        };

        function _handleWorkflowParameter(value, callback) {
            var re = /\$\{(.+?)\}/g;
            var match;
            while ((match = re.exec(String(value)))) {
                var wp_name = match[1];
                callback(_ensureWorkflowParameter(wp_name));
            }
        }

        _.each(this.steps, (step, i) => {
            _.each(this.parms[i], (input, name) => {
                _handleWorkflowParameter(input.value, (wp_input) => {
                    hasReplacementParametersInToolForm = true;
                    wp_input.links.push(step);
                    input.wp_linked = true;
                    input.type = "text";
                    input.cls = "ui-input-linked";
                });
            });
            _.each(step.replacement_parameters, (wp_name) => {
                if (this.parameterInputLabels.indexOf(wp_name) == -1) {
                    _ensureWorkflowParameter(wp_name);
                }
            });
        });

        // select fields are shown for dynamic fields if all putative data inputs are available,
        // or if an explicit reference is specified as data_ref and available
        _.each(this.steps, (step) => {
            if (step.step_type == "tool") {
                let dataResolved = true;
                visitInputs(step.inputs, (input, name, context) => {
                    const isRuntimeValue = input.value && input.value.__class__ == "RuntimeValue";
                    const isDataInput = ["data", "data_collection"].indexOf(input.type) != -1;
                    const dataRef = context[input.data_ref];
                    if (input.step_linked && !isDataStep(input.step_linked)) {
                        dataResolved = false;
                    }
                    if (input.options && ((input.options.length == 0 && !dataResolved) || input.wp_linked)) {
                        input.is_workflow = true;
                    }
                    if (dataRef) {
                        input.is_workflow =
                            (dataRef.step_linked && !isDataStep(dataRef.step_linked)) || input.wp_linked;
                    }
                    if ((isDataInput && !input.optional) || (!isDataInput && isRuntimeValue && !input.step_linked)) {
                        step.expanded = true;
                        hasOpenToolSteps = true;
                    }
                    if (isRuntimeValue) {
                        input.value = null;
                    }
                    input.flavor = "workflow";
                    if (!isRuntimeValue && !isDataInput && input.type !== "hidden" && !input.wp_linked) {
                        if (input.optional || (!isEmpty(input.value) && input.value !== "")) {
                            input.collapsible_value = input.value;
                            input.collapsible_preview = true;
                        }
                    }
                });
            }
        });
        this.hasOpenToolSteps = hasOpenToolSteps;
        this.hasReplacementParametersInToolForm = hasReplacementParametersInToolForm;
    }

    isConnected(stepId, inputName) {
        return this.parms[stepId][inputName].connected;
    }
}

/** Is data input module/step */
export function isDataStep(steps) {
    var lst = Array.isArray(steps) ? steps : [steps];
    for (var i = 0; i < lst.length; i++) {
        var step = lst[i];
        if (!step || !step.step_type || !step.step_type.startsWith("data")) {
            return false;
        }
    }
    return true;
}

/** Produces a dictionary of parameter replacements to be consumed by the form components */
export function getReplacements(inputs, stepData, wpData) {
    const params = {};
    visitInputs(inputs, (input, name) => {
        params[name] = input;
    });
    const replaceParams = {};
    _.each(params, (input, name) => {
        if (input.wp_linked || input.step_linked) {
            let newValue = null;
            if (input.step_linked) {
                _.each(input.step_linked, (sourceStep) => {
                    if (isDataStep(sourceStep)) {
                        const sourceData = stepData[sourceStep.index];
                        const value = sourceData && sourceData.input;
                        if (value) {
                            newValue = { values: [] };
                            _.each(value.values, (v) => {
                                newValue.values.push(v);
                            });
                        }
                    }
                });
                if (!input.multiple && newValue && newValue.values.length > 0) {
                    newValue = {
                        values: [newValue.values[0]],
                    };
                }
            }
            if (input.wp_linked) {
                newValue = input.value;
                const re = /\$\{(.+?)\}/g;
                let match;
                while ((match = re.exec(input.value))) {
                    const wpValue = wpData[match[1]];
                    if (wpValue) {
                        newValue = newValue.split(match[0]).join(wpValue);
                    }
                }
            }
            if (newValue !== undefined) {
                replaceParams[name] = newValue;
            }
        }
    });
    return replaceParams;
}
