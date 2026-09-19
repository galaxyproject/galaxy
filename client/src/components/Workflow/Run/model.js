import { escape } from "lodash";

import { visitInputs } from "@/components/Form/utilities";
import { isEmpty } from "@/utils/utils";

export class WorkflowRunModel {
    constructor(runData) {
        this.runData = runData;
        this.name = runData.name;
        this.workflowResourceParameters = runData.workflow_resource_parameters;
        this.hasWorkflowResourceParameters = Object.keys(this.workflowResourceParameters || {}).length > 0;
        this.historyId = runData.history_id;
        this.workflowId = runData.id;

        this.hasUpgradeMessages = runData.has_upgrade_messages;
        this.hasStepVersionChanges = Object.keys(runData.step_version_changes || {}).length > 0;

        this.steps = [];
        this.links = [];
        this.parms = [];
        this.wpInputs = {};
        this.parameterInputLabels = [];

        let hasOpenToolSteps = false;
        let hasReplacementParametersInToolForm = false;

        for (const [i, step] of Object.entries(runData.steps)) {
            const isParameterStep = step.step_type == "parameter_input";
            var title = `${parseInt(i) + 1}: ${step.step_label || step.step_name}`;
            if (step.annotation) {
                title += ` - ${step.annotation}`;
            }
            if (step.step_version) {
                title += ` (Galaxy Version ${step.step_version})`;
            }
            const merged = Object.assign(
                {
                    index: i,
                    fixed_title: escape(title),
                    expanded: i == 0 || isDataStep(step) || isParameterStep,
                    errors: step.messages,
                },
                step,
            );
            this.steps[i] = merged;
            this.links[i] = [];
            this.parms[i] = {};
            if (isParameterStep && step.step_label) {
                this.parameterInputLabels.push(step.step_label);
            }
        }

        // build linear index of step input pairs
        for (const [i, step] of Object.entries(this.steps)) {
            visitInputs(step.inputs, (input, name) => {
                this.parms[i][name] = input;
            });
        }

        // iterate through data input modules and collect linked sub steps
        for (const [i, step] of Object.entries(this.steps)) {
            for (const output_connection of step.output_connections || []) {
                for (const sub_step of Object.values(this.steps)) {
                    if (sub_step.step_index === output_connection.input_step_index) {
                        this.links[i].push(sub_step);
                    }
                }
            }
        }

        // convert all connected data inputs to hidden fields with proper labels,
        // and track the linked source step
        for (const [i, step] of Object.entries(this.steps)) {
            for (const [j] of Object.entries(this.steps)) {
                var connections_by_name = {};
                for (const connection of step.output_connections || []) {
                    if (this.steps[j].step_index === connection.input_step_index) {
                        connections_by_name[connection.input_name] = connection;
                    }
                }
                for (const [name, input] of Object.entries(this.parms[j])) {
                    var connection = connections_by_name[name];
                    if (connection) {
                        input.connected = true;
                        input.type = "hidden";
                        input.help = input.step_linked ? `${input.help}, ` : "";
                        input.help += `Connected to '${connection.output_name}' from Step ${parseInt(i) + 1}`;
                        input.step_linked = input.step_linked || [];
                        input.step_linked.push({ index: step.index, step_type: step.step_type });
                    }
                }
            }
        }

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

        for (const [i, step] of Object.entries(this.steps)) {
            for (const input of Object.values(this.parms[i])) {
                _handleWorkflowParameter(input.value, (wp_input) => {
                    hasReplacementParametersInToolForm = true;
                    wp_input.links.push(step);
                    input.wp_linked = true;
                    input.type = "text";
                    input.cls = "ui-input-linked";
                });
            }
            for (const wp_name of step.replacement_parameters || []) {
                if (this.parameterInputLabels.indexOf(wp_name) == -1) {
                    _ensureWorkflowParameter(wp_name);
                }
            }
        }

        // select fields are shown for dynamic fields if all putative data inputs are available,
        // or if an explicit reference is specified as data_ref and available
        for (const step of Object.values(this.steps)) {
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
        }
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
    for (const [name, input] of Object.entries(params)) {
        if (input.wp_linked || input.step_linked) {
            let newValue = null;
            if (input.step_linked) {
                for (const sourceStep of input.step_linked) {
                    if (isDataStep(sourceStep)) {
                        const sourceData = stepData[sourceStep.index];
                        const value = sourceData && sourceData.input;
                        if (value) {
                            newValue = { values: [] };
                            for (const v of value.values) {
                                newValue.values.push(v);
                            }
                        }
                    }
                }
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
    }
    return replaceParams;
}
