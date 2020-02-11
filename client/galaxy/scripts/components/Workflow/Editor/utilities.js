import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import WorkflowIcons from "components/Workflow/icons";
import FormWrappers from "mvc/workflow/workflow-forms";
import { hide_modal, show_message, show_modal } from "layout/modal";

export function buildDropdowns(workflow, id) {
    // On load, set the size to the pref stored in local storage if it exists
    var overview_size = localStorage.getItem("overview-size");
    if (overview_size !== undefined) {
        $(".workflow-overview").css({
            width: overview_size,
            height: overview_size
        });
    }

    // Stores the size of the overview into local storage when it's resized
    $(".workflow-overview").bind("dragend", function(e, d) {
        var op = $(this).offsetParent();
        var opo = op.offset();
        var new_size = Math.max(op.width() - (d.offsetX - opo.left), op.height() - (d.offsetY - opo.top));
        localStorage.setItem("overview-size", `${new_size}px`);
    });

    // Unload handler
    window.onbeforeunload = () => {
        if (workflow && workflow.has_changes) {
            return "There are unsaved changes to your workflow which will be lost.";
        }
    };
}

export function copyIntoWorkflow(workflow, id = null, stepCount = null) {
    const Galaxy = getGalaxyInstance();
    var _copy_into_workflow_ajax = function(workflow, workflowId) {
        // Load workflow definition
        show_message("Importing workflow", "progress");
        loadWorkflow(workflowId, null).then(data => {
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
        _copy_into_workflow_ajax(workflow, id);
    } else {
        // don't ruin the workflow by adding 50 steps unprompted.
        Galaxy.modal.show({
            title: _l("Warning"),
            body: `This will copy ${stepCount} new steps into your workflow.`,
            buttons: {
                Cancel: function() {
                    Galaxy.modal.hide();
                },
                Copy: function() {
                    Galaxy.modal.hide();
                    _copy_into_workflow_ajax(workflow, id);
                }
            }
        });
    }
}

export function showWarnings(data) {
    const body = $("<div/>").text(data.message);
    if (data.errors) {
        body.addClass("warningmark");
        var errlist = $("<ul/>");
        $.each(data.errors, (i, v) => {
            $("<li/>")
                .text(v)
                .appendTo(errlist);
        });
        body.append(errlist);
    } else {
        body.addClass("donemark");
    }
    if (data.errors) {
        show_modal("Saving workflow", body, {
            Ok: hide_modal
        });
    } else {
        hide_modal();
    }
}

export function showAttributes() {
    $(".right-content").hide();
    $("#edit-attributes").show();
}

export function showForm(workflow, content, node, datatypes) {
    const cls = "right-content";
    var id = `${cls}-${node.id}`;
    var $container = $(`#${cls}`);
    const Galaxy = getGalaxyInstance();
    if (content && $container.find(`#${id}`).length === 0) {
        var $el = $(`<div id="${id}" class="${cls}"/>`);
        content.node = node;
        content.workflow = workflow;
        content.datatypes = datatypes;
        content.icon = WorkflowIcons[node.type];
        content.cls = "ui-portlet-section";
        if (node) {
            var form_type = node.type == "tool" ? "Tool" : "Default";
            $el.append(new FormWrappers[form_type](content).form.$el);
            $container.append($el);
        } else {
            Galaxy.emit.debug("workflow-view::initialize()", "Node not found in workflow.");
        }
    }
    $(`.${cls}`).hide();
    $container.find(`#${id}`).show();
    $container.show();
    $container.scrollTop();
}

export function showUpgradeMessage(workflow, data) {
    // Determine if any parameters were 'upgraded' and provide message
    var upgrade_message = "";
    _.each(data.steps, (step, step_id) => {
        var details = "";
        if (step.errors) {
            details += `<li>${step.errors}</li>`;
        }
        _.each(data.upgrade_messages[step_id], m => {
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

export function showWorkflowParameters(workflow) {
    var parameter_re = /\$\{.+?\}/g;
    var workflow_parameters = [];
    var wf_parm_container = $("#workflow-parameters-container");
    var wf_parm_box = $("#workflow-parameters-box");
    var new_parameter_content = "";
    var matches = [];
    $.each(workflow.nodes, (k, node) => {
        if (node.config_form && node.config_form.inputs) {
            Utils.deepeach(node.config_form.inputs, d => {
                if (typeof d.value == "string") {
                    var form_matches = d.value.match(parameter_re);
                    if (form_matches) {
                        matches = matches.concat(form_matches);
                    }
                }
            });
        }
        if (node.post_job_actions) {
            $.each(node.post_job_actions, (k, pja) => {
                if (pja.action_arguments) {
                    $.each(pja.action_arguments, (k, action_argument) => {
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
            $.each(matches, (k, element) => {
                if ($.inArray(element, workflow_parameters) === -1) {
                    workflow_parameters.push(element);
                }
            });
        }
    });
    if (workflow_parameters && workflow_parameters.length !== 0) {
        $.each(workflow_parameters, (k, element) => {
            new_parameter_content += `<div>${element.substring(2, element.length - 1)}</div>`;
        });
        wf_parm_container.html(new_parameter_content);
        wf_parm_box.show();
    } else {
        wf_parm_container.html(new_parameter_content);
        wf_parm_box.hide();
    }
}

export function saveAs(workflow) {
    var body = $(
        '<form><label style="display:inline-block; width: 100%;">Save as name: </label><input type="text" id="workflow_rename" style="width: 80%;" autofocus/>' +
            '<br><label style="display:inline-block; width: 100%;">Annotation: </label><input type="text" id="wf_annotation" style="width: 80%;" /></form>'
    );
    show_modal("Save As a New Workflow", body, {
        OK: function() {
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
                    workflow_data: function() {
                        return JSON.stringify(workflow.to_simple());
                    }
                }
            })
                .done(id => {
                    window.onbeforeunload = undefined;
                    window.location = `${getAppRoot()}workflow/editor?id=${id}`;
                    hide_modal();
                })
                .fail(() => {
                    hide_modal();
                    alert("Saving this workflow failed. Please contact this site's administrator.");
                });
        },
        Cancel: hide_modal
    });
}
