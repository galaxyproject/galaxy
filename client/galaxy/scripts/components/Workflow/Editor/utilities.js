import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import _l from "utils/localization";
import Utils from "utils/utils";
import WorkflowIcons from "components/Workflow/icons";
import { DefaultForm, ToolForm } from "mvc/workflow/workflow-forms";
import { loadWorkflow } from "./services";
import { hide_modal, show_message, show_modal } from "layout/modal";
import Modal from "mvc/ui/ui-modal";

export function copyIntoWorkflow(workflow, id = null, stepCount = null) {
    const _copy_into_workflow_ajax = () => {
        // Load workflow definition
        show_message("Importing workflow", "progress");
        loadWorkflow(workflow, id, null).then((data) => {
            workflow.from_simple(data, false);
            // Determine if any parameters were 'upgraded' and provide message
            var upgrade_message = "";
            $.each(data.upgrade_messages, (k, v) => {
                upgrade_message += `<li>Step ${parseInt(k, 10) + 1}: ${workflow.nodes[k].name}<ul>`;
                $.each(v, (i, vv) => {
                    upgrade_message += `<li>${vv}</li>`;
                });
                upgrade_message += "</ul></li>";
            });
            if (upgrade_message) {
                show_modal(
                    "Subworkflow embedded with changes",
                    `Problems were encountered loading this workflow (possibly a result of tool upgrades). Please review the following parameters and then save.<ul>${upgrade_message}</ul>`,
                    { Continue: hide_modal }
                );
            } else {
                hide_modal();
            }
        });
    };
    if (stepCount < 2) {
        _copy_into_workflow_ajax();
    } else {
        // don't ruin the workflow by adding 50 steps unprompted.
        show_modal(_l("Warning"), `This will copy ${stepCount} new steps into your workflow.`, {
            Cancel: hide_modal,
            Copy: _copy_into_workflow_ajax,
        });
    }
}

export function showWarnings(data) {
    const body = $("<div/>").text(data.message);
    if (data.errors) {
        body.addClass("warningmark");
        var errlist = $("<ul/>");
        $.each(data.errors, (i, v) => {
            $("<li/>").text(v).appendTo(errlist);
        });
        body.append(errlist);
    } else {
        body.addClass("donemark");
    }
    if (data.errors) {
        show_modal("Saving workflow", body, {
            Ok: hide_modal,
        });
    } else {
        hide_modal();
    }
}

export function showAttributes() {
    $(".right-content").hide();
    $("#edit-attributes").show();
}

export function showForm(workflow, node, datatypes) {
    if (node && node.config_form) {
        const content = node.config_form;
        const cls = "right-content";
        var id = `${cls}-${node.id}`;
        var $container = $(`#${cls}`);
        if ($container.find(`#${id}`).length === 0) {
            var $el = $(`<div id="${id}" class="${cls}"/>`);
            content.node = node;
            content.workflow = workflow;
            content.datatypes = datatypes;
            content.icon = WorkflowIcons[node.type];
            content.cls = "ui-portlet-section";
            let formWrapper = null;
            if (node.type == "tool") {
                formWrapper = new ToolForm(content);
            } else {
                formWrapper = new DefaultForm(content);
            }
            $el.append(formWrapper.form.$el);
            $container.append($el);
        }
        $(`.${cls}`).hide();
        $container.find(`#${id}`).show();
        $container.show();
        $container.scrollTop();
    }
}

export function showUpgradeMessage(workflow, data) {
    // Determine if any parameters were 'upgraded' and provide message
    var upgrade_message = "";
    _.each(data.steps, (step, step_id) => {
        var details = "";
        if (step.errors) {
            details += `<li>${step.errors}</li>`;
        }
        _.each(data.upgrade_messages[step_id], (m) => {
            details += `<li>${m}</li>`;
        });
        if (details) {
            upgrade_message += `<li>Step ${parseInt(step_id, 10) + 1}: ${
                workflow.nodes[step_id].name
            }<ul>${details}</ul></li>`;
        }
    });
    if (upgrade_message) {
        show_modal(
            "Issues loading this workflow",
            `Please review the following issues, possibly resulting from tool upgrades or changes.<p><ul>${upgrade_message}</ul></p>`,
            { Continue: hide_modal }
        );
    } else {
        hide_modal();
    }
}

export function getWorkflowParameters(nodes) {
    const parameter_re = /\$\{.+?\}/g;
    const parameters = [];
    let matches = [];
    Object.entries(nodes).forEach(([k, node]) => {
        if (node.config_form && node.config_form.inputs) {
            Utils.deepeach(node.config_form.inputs, (d) => {
                if (typeof d.value == "string") {
                    var form_matches = d.value.match(parameter_re);
                    if (form_matches) {
                        matches = matches.concat(form_matches);
                    }
                }
            });
        }
        if (node.post_job_actions) {
            Object.entries(node.post_job_actions).forEach(([k, pja]) => {
                if (pja.action_arguments) {
                    Object.entries(pja.action_arguments).forEach(([k, action_argument]) => {
                        if (typeof action_argument === "string") {
                            const arg_matches = action_argument.match(parameter_re);
                            if (arg_matches) {
                                matches = matches.concat(arg_matches);
                            }
                        }
                    });
                }
            });
        }
        if (matches) {
            Object.entries(matches).forEach(([k, element]) => {
                if (parameters.indexOf(element) === -1) {
                    parameters.push(element);
                }
            });
        }
    });
    Object.entries(parameters).forEach(([k, element]) => {
        parameters[k] = element.substring(2, element.length - 1);
    });
    return parameters;
}

export function saveAs(workflow) {
    var body = $(
        '<form><label style="display:inline-block; width: 100%;">Save as name: </label><input type="text" id="workflow_rename" style="width: 80%;" autofocus/>' +
            '<br><label style="display:inline-block; width: 100%;">Annotation: </label><input type="text" id="wf_annotation" style="width: 80%;" /></form>'
    );
    show_modal("Save As a New Workflow", body, {
        OK: function () {
            var rename_name =
                $("#workflow_rename").val().length > 0 ? $("#workflow_rename").val() : `SavedAs_${workflow.name}`;
            var rename_annotation = $("#wf_annotation").val().length > 0 ? $("#wf_annotation").val() : "";
            $.ajax({
                url: `${getAppRoot()}workflow/save_workflow_as`,
                type: "POST",
                data: {
                    workflow_name: rename_name,
                    workflow_annotation: rename_annotation,
                    from_tool_form: true,
                    workflow_data: function () {
                        return JSON.stringify(workflow.to_simple());
                    },
                },
            })
                .done((id) => {
                    window.onbeforeunload = undefined;
                    window.location = `${getAppRoot()}workflow/editor?id=${id}`;
                    hide_modal();
                })
                .fail(() => {
                    hide_modal();
                    alert("Saving this workflow failed. Please contact this site's administrator.");
                });
        },
        Cancel: hide_modal,
    });
}

function getToolId(toolId) {
    if (toolId !== undefined && toolId !== null && toolId.indexOf("/") > -1) {
        let toolIdSlash = toolId.split("/");
        toolId = toolIdSlash[toolIdSlash.length - 2];
    }
    return toolId;
}

function get_workflow_path(wf_steps, current_node_id, current_node_name) {
        let steps = {};
        let step_names = {};
        for (let stp_idx in wf_steps.steps) {
            let step = wf_steps.steps[stp_idx];
            let input_connections = step.input_connections;
            step_names[step.id] = getToolId(step.content_id);
            for (let ic_idx in input_connections) {
                let ic = input_connections[ic_idx];
                if(ic !== null && ic !== undefined) {
                    let prev_conn = [];
                    for (let conn of ic) {
                        prev_conn.push(conn.id.toString());
                    }
                    steps[step.id.toString()] = prev_conn;
                }
            }
        }
        // recursive call to determine path
        function read_paths(node_id, ph) {
            for (let st in steps) {
                if (parseInt(st) === parseInt(node_id)) {
                    let parent_id = parseInt(steps[st][0]);
                    if (parent_id !== undefined && parent_id !== null) {
                        ph.push(parent_id);
                        if (steps[parent_id] !== undefined && steps[parent_id] !== null) {
                            read_paths(parent_id, ph);
                        }
                    }
                }
            }
            return ph;
        }
        let ph = [];
        let step_names_list = [];
        ph.push(current_node_id);
        ph = read_paths(current_node_id, ph);
        for (let s_idx of ph) {
            let s_name = step_names[s_idx.toString()];
            if (s_name !== undefined && s_name !== null) {
                step_names_list.push(s_name);
            }
        }
        return step_names_list.join(",");
}

export function getToolRecommendations(propsData) {
        let workflow_simple = propsData.node.app.to_simple(),
        node = propsData.node,
        toolId = getToolId(node.content_id);
        console.log(workflow_simple);
        console.log(node);
        let tool_sequence = get_workflow_path(workflow_simple, node.id, toolId);
        console.log(tool_sequence);
        
        // remove ui-modal if present
        let $modal = $(".modal-tool-recommendation");
        if ($modal.length > 0) {
            $modal.remove();
        }
        // create new modal
        let modal = new Modal.View({
            title: "Recommended tools",
            body: "<div> Loading tools ... </div>",
            height: "230",
            width: "250",
            closing_events: true,
            title_separator: true        
        });
        modal.$el.addClass("modal-tool-recommendation");
        modal.$el.find(".modal-header").attr("title", "The recommended tools are shown in the decreasing order of their scores predicted using machine learning analysis on workflows. A tool with a higher score (closer to 100%) may fit better as the following tool than a tool with a lower score. Please click on one of the following/recommended tools to have it on the workflow editor.");
        modal.$el.find(".modal-body").css("overflow", "auto");
        modal.show();
        // fetch recommended tools
        Utils.request({
            type: "POST",
            url: `${getAppRoot()}api/workflows/get_tool_predictions`,
            data: {"tool_sequence": tool_sequence},
            success: function(data) {
                let predTemplate = "<div>";
                let predictedData = data.predicted_data;
                let outputDatatypes = predictedData["o_extensions"];
                let predictedDataChildren = predictedData.children;
                let noRecommendationsMessage = "No tool recommendations";
                if (predictedDataChildren.length > 0) {
                    let compatibleTools = {};
                    // filter results based on datatype compatibility
                    for (const [index, name_obj] of predictedDataChildren.entries()) {
                        let inputDatatypes = name_obj["i_extensions"];
                        for (const out_t of outputDatatypes.entries()) {
                            for(const in_t of inputDatatypes.entries()) {
                                if ((propsData.node.app.isSubType(out_t[1], in_t[1]) === true) ||
                                     out_t[1] === "input" ||
                                     out_t[1] === "_sniff_" ||
                                     out_t[1] === "input_collection") {
                                    compatibleTools[name_obj["tool_id"]] = name_obj["name"];
                                    break
                                }
                            }
                        }
                    }
                    predTemplate += "<div>";
                    if (Object.keys(compatibleTools).length > 0 && predictedData["is_deprecated"] === false) {
                        for (let id in compatibleTools) {
                            predTemplate += "<i class='fa mr-1 fa-wrench'></i><a href='#' title='Click to open the tool' class='pred-tool panel-header-button' id=" + "'" + id + "'" + ">" + compatibleTools[id];
                            predTemplate += "</a></br>";
                        }
                    }
                    else if (predictedData["is_deprecated"] === true) {
                        predTemplate += predictedData["message"];
                    }
                    else {
                        predTemplate += noRecommendationsMessage;
                    }
                    predTemplate += "</div>";
                }
                else {
                    predTemplate += noRecommendationsMessage; 
                }
                predTemplate += "</div>";
                modal.$body.html(predTemplate);
                $(".pred-tool").click(e => {
                    workflow_globals.app.add_node_for_tool(e.target.id, e.target.id);
                    modal.hide();
                });
            }
        });
    }
