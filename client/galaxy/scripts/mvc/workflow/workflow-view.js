import _ from "underscore";
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Workflow from "mvc/workflow/workflow-manager";
import WorkflowCanvas from "mvc/workflow/workflow-canvas";
import { Node } from "mvc/workflow/workflow-node";
import WorkflowIcons from "mvc/workflow/workflow-icons";
import FormWrappers from "mvc/workflow/workflow-forms";
import { mountWorkflowNode } from "components/Workflow/Editor/mount";
import "ui/editable-text";

import { hide_modal, show_message, show_modal } from "layout/modal";

// TODO; tie into Galaxy state?
window.workflow_globals = window.workflow_globals || {};

const DEFAULT_INVOCATION_REPORT = `
# Workflow Execution Report

## Workflow Inputs
\`\`\`galaxy
invocation_inputs()
\`\`\`

## Workflow Outputs
\`\`\`galaxy
invocation_outputs()
\`\`\`

## Workflow
\`\`\`galaxy
workflow_display()
\`\`\`
`;

export class WorkflowView {
    constructor(options, reportsEditor = {}) {
        var self = (window.workflow_globals.app = this);
        this.options = options;
        this.reportsEditor = reportsEditor;

        // Canvas overview management
        this.canvas_manager = window.workflow_globals.canvas_manager = new WorkflowCanvas(
            this,
            $("#canvas-viewport"),
            $("#overview")
        );

        // Initialize workflow state
        this.reset();

        // get available datatypes for post job action options
        this.datatypes = JSON.parse(
            $.ajax({
                url: `${getAppRoot()}api/datatypes`,
                async: false
            }).responseText
        );

        // get datatype mapping options
        this.datatypes_mapping = JSON.parse(
            $.ajax({
                url: `${getAppRoot()}api/datatypes/mapping`,
                async: false
            }).responseText
        );

        // set mapping sub lists
        this.ext_to_type = this.datatypes_mapping.ext_to_class_name;
        this.type_to_type = this.datatypes_mapping.class_to_classes;

        this.get_workflow_versions = function() {
            const _workflow_version_dropdown = {};
            const workflow_versions = JSON.parse(
                $.ajax({
                    url: `${getAppRoot()}api/workflows/${self.options.id}/versions`,
                    async: false
                }).responseText
            );

            for (let i = 0; i < workflow_versions.length; i++) {
                const current_wf = workflow_versions[i];
                let version_text = `Version ${current_wf.version}, ${current_wf.steps} steps`;
                let selected = false;
                if (i == self.workflow.workflow_version) {
                    version_text = `${version_text} (active)`;
                    selected = true;
                }
                _workflow_version_dropdown[version_text] = {
                    version: i,
                    selected: selected
                };
            }
            return _workflow_version_dropdown;
        };

        this.build_version_select = function() {
            const versions = this.get_workflow_versions();
            $("#workflow-version-switch").empty();
            $.each(versions, function(k, v) {
                $("#workflow-version-switch").append(
                    $("<option></option>")
                        .html(k)
                        .val(v.version)
                        .selected(v.selected)
                );
            });
            $("#workflow-version-switch").on("change", function() {
                $("#workflow-version-switch").unbind("change");
                if (this.value != self.workflow.workflow_version) {
                    if (self.workflow && self.workflow.has_changes) {
                        const r = window.confirm(
                            "There are unsaved changes to your workflow which will be lost. Continue ?"
                        );
                        if (r == false) {
                            // We rebuild the version select list, to reset the selected version
                            self.build_version_select();
                            return;
                        }
                    }
                    self.load_workflow(self.options.id, this.value);
                }
            });
        };

        this.load_workflow = function load_workflow(id, version) {
            this._workflowLoadAjax(id, version, {
                success: function(data) {
                    self.reset();
                    self.workflow.from_simple(data, true);
                    const report = data.report || {};
                    const markdown = report.markdown || DEFAULT_INVOCATION_REPORT;
                    self.reportsEditor.input = markdown;
                    self.workflow.has_changes = false;
                    self.workflow.fit_canvas_to_nodes();
                    self.scroll_to_nodes();
                    self.canvas_manager.draw_overview();
                    self.build_version_select();

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
                                self.workflow.nodes[step_id].name
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
                    self.showWorkflowParameters();
                },
                error: function(response) {
                    show_modal("Loading workflow failed.", response.err_msg, {
                        Ok: function(response) {
                            window.onbeforeunload = undefined;
                            window.document.location = `${getAppRoot()}workflows/list`;
                        }
                    });
                },
                beforeSubmit: function(data) {
                    show_message("Loading workflow", "progress");
                }
            });
        };

        // Load workflow definition
        this.load_workflow(self.options.id, self.options.version);

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
            if (self.workflow && self.workflow.has_changes) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        };
    }

    copy_into_workflow(id = null, stepCount = null) {
        const Galaxy = getGalaxyInstance();
        if (stepCount < 2) {
            this._copy_into_workflow_ajax(id);
        } else {
            // don't ruin the workflow by adding 50 steps unprompted.
            var self = this;
            Galaxy.modal.show({
                title: _l("Warning"),
                body: `This will copy ${stepCount} new steps into your workflow.`,
                buttons: {
                    Cancel: function() {
                        Galaxy.modal.hide();
                    },
                    Copy: function() {
                        Galaxy.modal.hide();
                        self._copy_into_workflow_ajax(id);
                    }
                }
            });
        }
    }

    _copy_into_workflow_ajax(workflowId) {
        // Load workflow definition
        var self = this;
        this._workflowLoadAjax(workflowId, null, {
            success: function(data) {
                self.workflow.from_simple(data, false);
                // Determine if any parameters were 'upgraded' and provide message
                var upgrade_message = "";
                $.each(data.upgrade_messages, (k, v) => {
                    upgrade_message += `<li>Step ${parseInt(k, 10) + 1}: ${self.workflow.nodes[k].name}<ul>`;
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
            },
            beforeSubmit: function() {
                show_message("Importing workflow", "progress");
            }
        });
    }

    // Global state for the whole workflow
    reset() {
        if (this.workflow) {
            this.workflow.remove_all();
        }
        this.workflow = window.workflow_globals.workflow = new Workflow(this, $("#canvas-container"));
    }

    scroll_to_nodes() {
        var cv = $("#canvas-viewport");
        var cc = $("#canvas-container");
        var top;
        var left;
        if (cc.width() < cv.width()) {
            left = (cv.width() - cc.width()) / 2;
        } else {
            left = 0;
        }
        if (cc.height() < cv.height()) {
            top = (cv.height() - cc.height()) / 2;
        } else {
            top = 0;
        }
        cc.css({ left: left, top: top });
    }

    _workflowLoadAjax(workflowId, version, options) {
        $.ajax(
            Utils.merge(options, {
                url: `${getAppRoot()}workflow/load_workflow`,
                data: { id: workflowId, _: "true", version: version },
                dataType: "json",
                cache: false
            })
        );
    }

    _moduleInitAjax(node, request_data) {
        var self = this;
        Utils.request({
            type: "POST",
            url: `${getAppRoot()}api/workflows/build_module`,
            data: request_data,
            success: function(data) {
                const Galaxy = getGalaxyInstance();
                node.init_field_data(data);
                node.update_field_data(data);
                // Post init/update, for new modules we want to default to
                // nodes being outputs
                // TODO: Overhaul the handling of all this when we modernize
                // the editor, replace callout image manipulation with a simple
                // class toggle, etc.
                $.each(node.output_terminals, (ot_id, ot) => {
                    node.addWorkflowOutput(ot.name);
                    var callout = $(node.element).find(`.callout.${ot.name.replace(/(?=[()])/g, "\\")}`);
                    callout.find("img").attr("src", `${Galaxy.root}static/images/fugue/asterisk-small.png`);
                });
                self.workflow.activate_node(node);
            }
        });
    }

    // Add a new step to the workflow by tool id
    add_node_for_tool(id, title) {
        var node = this.workflow.create_node("tool", title, id);
        this._moduleInitAjax(node, {
            type: "tool",
            tool_id: id,
            _: "true"
        });
    }

    // Add a new step to the workflow by tool id
    add_node_for_subworkflow(id, title) {
        var node = this.workflow.create_node("subworkflow", title, id);
        this._moduleInitAjax(node, {
            type: "subworkflow",
            content_id: id,
            _: "true"
        });
    }

    add_node_for_module(type, title) {
        var node = this.workflow.create_node(type, title);
        this._moduleInitAjax(node, { type: type, _: "true" });
    }

    display_file_list(node) {
        var addlist = "<select id='node_data_list' name='node_data_list'>";
        for (var out_terminal in node.output_terminals) {
            addlist += `<option value='${out_terminal}'>${out_terminal}</option>`;
        }
        addlist += "</select>";
        return addlist;
    }

    showWorkflowParameters() {
        var parameter_re = /\$\{.+?\}/g;
        var workflow_parameters = [];
        var wf_parm_container = $("#workflow-parameters-container");
        var wf_parm_box = $("#workflow-parameters-box");
        var new_parameter_content = "";
        var matches = [];
        $.each(this.workflow.nodes, (k, node) => {
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

    showAttributes() {
        $(".right-content").hide();
        $("#edit-attributes").show();
    }

    showForm(content, node) {
        const cls = "right-content";
        var id = `${cls}-${node.id}`;
        var $container = $(`#${cls}`);
        const Galaxy = getGalaxyInstance();
        if (content && $container.find(`#${id}`).length === 0) {
            var $el = $(`<div id="${id}" class="${cls}"/>`);
            content.node = node;
            content.workflow = this.workflow;
            content.datatypes = this.datatypes;
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

    isSubType(child, parent) {
        child = this.ext_to_type[child];
        parent = this.ext_to_type[parent];
        return this.type_to_type[child] && parent in this.type_to_type[child];
    }

    report_changed(report_markdown) {
        this.workflow.has_changes = true;
        this.workflow.report.markdown = report_markdown;
    }

    save_current_workflow() {
        const self = this;
        show_message("Saving workflow", "progress");
        self.workflow.check_changes_in_active_form();
        if (!self.workflow.has_changes) {
            hide_modal();
            return;
        }
        self.workflow.rectify_workflow_outputs();
        Utils.request({
            url: `${getAppRoot()}api/workflows/${self.options.id}`,
            type: "PUT",
            data: { workflow: self.workflow.to_simple(), from_tool_form: true },
            success: function(data) {
                var body = $("<div/>").text(data.message);
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
                self.workflow.name = data.name;
                self.workflow.has_changes = false;
                self.workflow.stored = true;
                self.workflow.workflow_version = data.version;
                self.showWorkflowParameters();
                self.build_version_select();
                if (data.errors) {
                    show_modal("Saving workflow", body, {
                        Ok: hide_modal
                    });
                } else {
                    hide_modal();
                }
            },
            error: function(response) {
                show_modal("Saving workflow failed.", response.err_msg, { Ok: hide_modal });
            }
        });
    }

    workflow_save_as() {
        const self = this;
        var body = $(
            '<form><label style="display:inline-block; width: 100%;">Save as name: </label><input type="text" id="workflow_rename" style="width: 80%;" autofocus/>' +
                '<br><label style="display:inline-block; width: 100%;">Annotation: </label><input type="text" id="wf_annotation" style="width: 80%;" /></form>'
        );
        show_modal("Save As a New Workflow", body, {
            OK: function() {
                var rename_name =
                    $("#workflow_rename").val().length > 0
                        ? $("#workflow_rename").val()
                        : `SavedAs_${self.workflow.name}`;
                var rename_annotation = $("#wf_annotation").val().length > 0 ? $("#wf_annotation").val() : "";
                $.ajax({
                    url: `${getAppRoot()}workflow/save_workflow_as`,
                    type: "POST",
                    data: {
                        workflow_name: rename_name,
                        workflow_annotation: rename_annotation,
                        from_tool_form: true,
                        workflow_data: function() {
                            return JSON.stringify(self.workflow.to_simple());
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

    layout_editor() {
        this.workflow.layout();
        this.workflow.fit_canvas_to_nodes();
        this.scroll_to_nodes();
        this.canvas_manager.draw_overview();
    }

    prebuildNode(type, title_text, content_id) {
        var self = this;

        // Create node wrapper
        const container = document.createElement("div");
        container.className = "toolForm toolFormInCanvas";
        document.getElementById("canvas-container").appendChild(container);
        var $f = $(container);

        // Create backbone model and view
        var node = new Node(this, { element: $f });
        node.type = type;
        node.content_id = content_id;

        // Mount node component as child dom to node wrapper
        const child = document.createElement("div");
        container.appendChild(child);
        mountWorkflowNode(child, {
            id: content_id,
            type: type,
            title: title_text,
            node: node
        });

        // Set initial scroll position
        $f.css("left", $(window).scrollLeft() + 20);
        $f.css("top", $(window).scrollTop() + 20);

        // Position in container
        var o = $("#canvas-container").position();
        var p = $("#canvas-container").parent();
        var width = $f.outerWidth() + 50;
        var height = $f.height();
        $f.css({
            left: -o.left + p.width() / 2 - width / 2,
            top: -o.top + p.height() / 2 - height / 2
        });
        $f.css("width", width);
        $f.bind("dragstart", () => {
            self.workflow.activate_node(node);
        })
            .bind("dragend", function() {
                self.workflow.node_changed(this);
                self.workflow.fit_canvas_to_nodes();
                self.canvas_manager.draw_overview();
            })
            .bind("dragclickonly", () => {
                self.workflow.activate_node(node);
            })
            .bind("drag", function(e, d) {
                // Move
                var po = $(this)
                    .offsetParent()
                    .offset();
                // Find relative offset and scale by zoom
                var x = (d.offsetX - po.left) / self.canvas_manager.canvasZoom;
                var y = (d.offsetY - po.top) / self.canvas_manager.canvasZoom;
                $(this).css({ left: x, top: y });
                // Redraw
                $(this)
                    .find(".terminal")
                    .each(function() {
                        this.terminal.redraw();
                    });
            });
        return node;
    }
}
