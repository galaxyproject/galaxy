import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import Utils from "utils/utils";
import Workflow from "mvc/workflow/workflow-manager";
import WorkflowCanvas from "mvc/workflow/workflow-canvas";
import Node from "mvc/workflow/workflow-node";
import WorkflowIcons from "mvc/workflow/workflow-icons";
import FormWrappers from "mvc/workflow/workflow-forms";
import Ui from "mvc/ui/ui-misc";
import async_save_text from "utils/async-save-text";
import "ui/editable-text";

import { hide_modal, show_message, show_modal } from "layout/modal";
import { make_popupmenu } from "ui/popupmenu";

// TODO; tie into Galaxy state?
window.workflow_globals = window.workflow_globals || {};

const reportHelp = `
<div>
<h3>Overview</h3>

<p>
    This document Markdown document will be used to generate a report
    for invocations of this workflow. This document should be Markdown
    with embedded command for extracting and displaying parts of the workflow,
    its invocation metadata, its inputs and outputs, etc.. For an overview
    of standard Markdown visit the <a href="https://commonmark.org/help/tutorial/">commonmark.org
    tutorial</a>.
</p>

<p>
    The Galaxy extensions to Markdown are represented as code blocks, these blocks start
    with the line <tt>\`\`\`galaxy</tt> and end with the line <tt>\`\`\`</tt> and have a
    command with arguments that reference parts of the workflow in the middle.
</p>

<h3>Workflow Commands</h3>

<p>
    These commands to do not take any arguments and reference the whole workflow. For
    instance, the following example would display a representation of the workflow in the
    resulting report:
</p>

<pre>
\`\`\`galaxy
workflow_display()
\`\`\`
</pre>
<dl>
<dt><tt>workflow_display</tt></dt>
<dd>Embed a description of the workflow itself in the resulting report.</dd>
<dt><tt>invocation_inputs</tt></dt>
<dd>Embed the labeled workflow inputs in the resulting report.</dd>
<dt><tt>invocation_outputs</tt></dt>
<dd>Embed the labeled workflow outputs in the resulting report.</dd>
</dl>

<h3>Step Commands</h3>

<p>
    These commands reference a workflow step label and refer to job corresponding
    to that step. A current limitation is the report will break if these refer to
    a collection mapping step, these must identify a single job. For instance, the
    following example would show the job parameters the step labeled 'qc' was run
    with:
</p>

<pre>
\`\`\`galaxy
job_parameters(step=qc)
\`\`\`
</pre>


<dt><tt>tool_stderr</tt></dt>
<dd>Embed the tool standard error stream for this step in the resulting report.</dd>
<dt><tt>tool_stdout</tt></dt>
<dd>Embed the tool standard output stream for this step in the resulting report.</dd>
<dt><tt>job_metrics</tt></dt>
<dd>Embed the job metrics for this step in the resulting report (if user has permission).</dd>
<dt><tt>job_parameters</tt></dt>
<dd>Embed the tool parameters for this step in the resulting report.</dd>

<h3>Input/Output Commands</h3>

<p>
    These commands reference a workflow input or output by label. For instance, the
    following example would display the dataset collection corresponding to output "Merged BAM":
</p>

<pre>
\`\`\`galaxy
history_dataset_collection_display(output="Merged Bam")
\`\`\`
</pre>

<dt><tt>history_dataset_display</tt></dt>
<dd>Embed a dataset description in the resulting report.</dd>
<dt><tt>history_dataset_collection_display</tt></dt>
<dd>Embed a dataset collection description in the resulting report.</dd>
<dt><tt>history_dataset_as_image</tt></dt>
<dd>Embed a dataset as an image in the resulting report - the dataset should be an image datatype.</dd>
<dt><tt>history_dataset_peek</tt></dt>
<dd>Embed Galaxy's metadata attribute 'peek' into the resulting report - this is datatype dependent metadata but usually this is a few lines from the start of a file.</dd>
<dt><tt>history_dataset_info</tt></dt>
<dd>Embed Galaxy's metadata attribute 'info' into the resulting report - this is datatype dependent metadata but usually this is the program output that generated the dataset.</dd>
</dl>
</div>
`;

// Reset tool search to start state.
function reset_tool_search(initValue) {
    // Function may be called in top frame or in tool_menu_frame;
    // in either case, get the tool menu frame.
    var tool_menu_frame = $("#galaxy_tools").contents();
    if (tool_menu_frame.length === 0) {
        tool_menu_frame = $(document);
        // Remove classes that indicate searching is active.
        $(this).removeClass("search_active");
        tool_menu_frame.find(".toolTitle").removeClass("search_match");

        // Reset visibility of tools and labels.
        tool_menu_frame.find(".toolSectionBody").hide();
        tool_menu_frame.find(".toolTitle").show();
        tool_menu_frame.find(".toolPanelLabel").show();
        tool_menu_frame.find(".toolSectionWrapper").each(function() {
            if ($(this).attr("id") !== "recently_used_wrapper") {
                // Default action.
                $(this).show();
            } else if ($(this).hasClass("user_pref_visible")) {
                $(this).show();
            }
        });
        tool_menu_frame.find("#search-no-results").hide();

        // Reset search input.
        tool_menu_frame.find("#search-spinner").hide();
        tool_menu_frame.find("#search-clear-btn").show();
        if (initValue) {
            var search_input = tool_menu_frame.find("#tool-search-query");
            search_input.val("search tools");
        }
    }
}

function add_node_icon($to_el, nodeType) {
    var iconStyle = WorkflowIcons[nodeType];
    if (iconStyle) {
        var $icon = $('<i class="icon fa">&nbsp;</i>').addClass(iconStyle);
        $to_el.before($icon);
    }
}

// create form view
export default Backbone.View.extend({
    initialize: function(options) {
        var self = (window.workflow_globals.app = this);
        this.options = options;
        this.urls = (options && options.urls) || {};
        var workflow_index = self.urls.workflow_index;
        var save_current_workflow = (eventObj, success_callback) => {
            show_message("Saving workflow", "progress");
            self.workflow.check_changes_in_active_form();
            if (!self.workflow.has_changes) {
                hide_modal();
                if (success_callback) {
                    success_callback();
                }
                return;
            }
            self.workflow.rectify_workflow_outputs();
            Utils.request({
                url: `${getAppRoot()}api/workflows/${self.options.id}`,
                type: "PUT",
                data: { workflow: self.workflow.to_simple() },
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
                        if (success_callback) {
                            success_callback();
                        }
                        hide_modal();
                    }
                },
                error: function(response) {
                    show_modal("Saving workflow failed.", response.err_msg, { Ok: hide_modal });
                }
            });
        };

        // Clear search by clicking X button
        $("#search-clear-btn").click(function() {
            $("#tool-search-query").val("");
            reset_tool_search(false);
        });

        // Init searching.
        $("#tool-search-query")
            .click(function() {
                $(this).focus();
                $(this).select();
            })
            .keyup(function(e) {
                // If ESC is pressed clear the search field
                if (e.keyCode == 27) {
                    this.value = "";
                }
                // Remove italics.
                $(this).css("font-style", "normal");
                // Don't update if same value as last time
                if (this.value.length < 3) {
                    reset_tool_search(false);
                } else if (this.value != this.lastValue) {
                    // Add class to denote that searching is active.
                    $(this).addClass("search_active");
                    // input.addClass(config.loadingClass);
                    // Add '*' to facilitate partial matching.
                    var q = this.value;
                    // Stop previous ajax-request
                    if (this.timer) {
                        window.clearTimeout(this.timer);
                    }
                    // Start a new ajax-request in X ms
                    $("#search-spinner").show();
                    $("#search-clear-btn").hide();
                    this.timer = window.setTimeout(() => {
                        $.get(
                            self.urls.tool_search,
                            { q: q },
                            data => {
                                // input.removeClass(config.loadingClass);
                                // Show live-search if results and search-term aren't empty
                                $("#search-no-results").hide();
                                // Hide all tool sections.
                                $(".toolSectionWrapper").hide();
                                // This hides all tools but not workflows link (which is in a .toolTitle div).
                                $(".toolSectionWrapper")
                                    .find(".toolTitle")
                                    .hide();
                                if (data.length !== 0) {
                                    // Map tool ids to element ids and join them.
                                    var s = $.map(data, (n, i) => `link-${n}`);
                                    // First pass to show matching tools and their parents.
                                    $(s).each((index, id) => {
                                        // Add class to denote match.
                                        $(`[id='${id}']`)
                                            .parent()
                                            .addClass("search_match");
                                        $(`[id='${id}']`)
                                            .parent()
                                            .show()
                                            .parent()
                                            .parent()
                                            .show()
                                            .parent()
                                            .show();
                                    });
                                    // Hide labels that have no visible children.
                                    $(".toolPanelLabel").each(function() {
                                        var this_label = $(this);
                                        var next = this_label.next();
                                        var no_visible_tools = true;
                                        // Look through tools following label and, if none are visible, hide label.
                                        while (next.length !== 0 && next.hasClass("toolTitle")) {
                                            if (next.is(":visible")) {
                                                no_visible_tools = false;
                                                break;
                                            } else {
                                                next = next.next();
                                            }
                                        }
                                        if (no_visible_tools) {
                                            this_label.hide();
                                        }
                                    });
                                } else {
                                    $("#search-no-results").show();
                                }
                                $("#search-spinner").hide();
                                $("#search-clear-btn").show();
                            },
                            "json"
                        );
                    }, 400);
                }
                this.lastValue = this.value;
            });

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
                            window.document.location = workflow_index;
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
        if (make_popupmenu) {
            $("#workflow-run-button").click(
                () => (window.location = `${getAppRoot()}workflows/run?id=${self.options.id}`)
            );
            $("#workflow-save-button").click(() => save_current_workflow());
            $("#workflow-report-button").click(() => edit_report());
            $("#workflow-report-help-button").click(() => show_report_help());
            $("#workflow-canvas-button").click(() => edit_canvas());
            make_popupmenu($("#workflow-options-button"), {
                "Save As": workflow_save_as,
                "Edit Attributes": function() {
                    self.workflow.clear_active_node();
                },
                "Auto Re-layout": layout_editor,
                Download: {
                    url: `${getAppRoot()}api/workflows/${self.options.id}/download?format=json-download`,
                    action: function() {}
                }
            });
        }

        /******************************************** Issue 3000*/
        function workflow_save_as() {
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
                        url: self.urls.workflow_save_as,
                        type: "POST",
                        data: {
                            workflow_name: rename_name,
                            workflow_annotation: rename_annotation,
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

        function layout_editor() {
            self.workflow.layout();
            self.workflow.fit_canvas_to_nodes();
            self.scroll_to_nodes();
            self.canvas_manager.draw_overview();
        }

        function edit_report() {
            $(".workflow-canvas-content").hide();
            $(".workflow-report-content").show();
        }

        function show_report_help() {
            const reportHelpBody = $(reportHelp);
            show_modal("Workflow Invocation Report Help", reportHelpBody, {
                Ok: hide_modal
            });
        }

        function edit_canvas() {
            $(".workflow-canvas-content").show();
            $(".workflow-report-content").hide();
        }

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

        if (this.options.workflows.length > 0) {
            $("#left")
                .find(".toolMenu")
                .append(this._buildToolPanelWorkflows());
        }

        // Tool menu
        $("div.toolSectionBody").hide();
        $("div.toolSectionTitle > span").wrap("<a href='javascript:void(0)' role='button'></a>");
        var last_expanded = null;
        $("div.toolSectionTitle").each(function() {
            var body = $(this).next("div.toolSectionBody");
            $(this).click(() => {
                if (body.is(":hidden")) {
                    if (last_expanded) last_expanded.slideUp("fast");
                    last_expanded = body;
                    body.slideDown("fast");
                } else {
                    body.slideUp("fast");
                    last_expanded = null;
                }
            });
        });

        // Rename async.
        async_save_text("workflow-name", "workflow-name", self.urls.rename_async, "new_name");

        // Tag async. Simply have the workflow edit element generate a click on the tag element to activate tagging.
        $("#workflow-tag").click(() => {
            $(".tag-area").click();
            return false;
        });
        // Annotate async.
        async_save_text(
            "workflow-annotation",
            "workflow-annotation",
            self.urls.annotate_async,
            "new_annotation",
            25,
            true,
            4
        );
    },

    _buildToolPanelWorkflows: function() {
        var self = this;
        var $section = $(
            '<div class="toolSectionWrapper">' +
                '<div class="toolSectionTitle">' +
                '<a href="javascript:void(0)" role="button"><span>Workflows</span></a>' +
                "</div>" +
                '<div class="toolSectionBody">' +
                '<div class="toolSectionBg"/>' +
                "</div>" +
                "</div>"
        );
        _.each(this.options.workflows, workflow => {
            if (workflow.id !== self.options.id) {
                var copy = new Ui.Button({
                    icon: "fa fa-copy",
                    cls: "ui-button-icon-plain",
                    tooltip: _l("Copy and insert individual steps"),
                    onclick: function() {
                        const Galaxy = getGalaxyInstance();
                        if (workflow.step_count < 2) {
                            self.copy_into_workflow(workflow.id, workflow.name);
                        } else {
                            // don't ruin the workflow by adding 50 steps unprompted.
                            Galaxy.modal.show({
                                title: _l("Warning"),
                                body: `This will copy ${workflow.step_count} new steps into your workflow.`,
                                buttons: {
                                    Cancel: function() {
                                        Galaxy.modal.hide();
                                    },
                                    Copy: function() {
                                        Galaxy.modal.hide();
                                        self.copy_into_workflow(workflow.id, workflow.name);
                                    }
                                }
                            });
                        }
                    }
                });
                var $add = $("<a/>")
                    .attr("href", "javascript:void(0)")
                    .attr("role", "button")
                    .html(workflow.name)
                    .on("click", () => {
                        self.add_node_for_subworkflow(workflow.latest_id, workflow.name);
                    });
                $section.find(".toolSectionBg").append(
                    $("<div/>")
                        .addClass("toolTitle")
                        .append($add)
                        .append(copy.$el)
                );
            }
        });
        return $section;
    },

    copy_into_workflow: function(workflowId) {
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
            beforeSubmit: function(data) {
                show_message("Importing workflow", "progress");
            }
        });
    },

    // Global state for the whole workflow
    reset: function() {
        if (this.workflow) {
            this.workflow.remove_all();
        }
        this.workflow = window.workflow_globals.workflow = new Workflow(this, $("#canvas-container"));
    },

    scroll_to_nodes: function() {
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
    },

    _workflowLoadAjax: function(workflowId, version, options) {
        $.ajax(
            Utils.merge(options, {
                url: this.urls.load_workflow,
                data: { id: workflowId, _: "true", version: version },
                dataType: "json",
                cache: false
            })
        );
    },

    _moduleInitAjax: function(node, request_data) {
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
    },

    // Add a new step to the workflow by tool id
    add_node_for_tool: function(id, title) {
        var node = this.workflow.create_node("tool", title, id);
        this._moduleInitAjax(node, {
            type: "tool",
            tool_id: id,
            _: "true"
        });
    },

    // Add a new step to the workflow by tool id
    add_node_for_subworkflow: function(id, title) {
        var node = this.workflow.create_node("subworkflow", title, id);
        this._moduleInitAjax(node, {
            type: "subworkflow",
            content_id: id,
            _: "true"
        });
    },

    add_node_for_module: function(type, title) {
        var node = this.workflow.create_node(type, title);
        this._moduleInitAjax(node, { type: type, _: "true" });
    },

    display_file_list: function(node) {
        var addlist = "<select id='node_data_list' name='node_data_list'>";
        for (var out_terminal in node.output_terminals) {
            addlist += `<option value='${out_terminal}'>${out_terminal}</option>`;
        }
        addlist += "</select>";
        return addlist;
    },

    showWorkflowParameters: function() {
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
    },

    showAttributes: function() {
        $(".right-content").hide();
        $("#edit-attributes").show();
    },

    showForm: function(content, node) {
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
    },

    isSubType: function(child, parent) {
        child = this.ext_to_type[child];
        parent = this.ext_to_type[parent];
        return this.type_to_type[child] && parent in this.type_to_type[child];
    },

    prebuildNode: function(type, title_text, content_id) {
        var self = this;
        var $f = $(`<div class='toolForm toolFormInCanvas'/>`);
        var $title = $(
            `<div class='toolFormTitle unselectable'><span class='nodeTitle'>${title_text}</span><span class="sr-only">&nbspNode</span></div>`
        );
        add_node_icon($title.find(".nodeTitle"), type);
        $f.append($title);
        $f.css("left", $(window).scrollLeft() + 20);
        $f.css("top", $(window).scrollTop() + 20);
        $f.append($("<div class='toolFormBody'></div>"));
        var node = new Node(this, { element: $f });
        node.type = type;
        node.content_id = content_id;
        var tmp = `<div><img alt="loading" height='16' align='middle' src='${getAppRoot()}static/images/loading_small_white_bg.gif'/> loading tool info...</div>`;
        $f.find(".toolFormBody").append(tmp);
        // Fix width to computed width
        // Now add floats
        var buttons = $("<div class='buttons' style='float: right;'></div>");
        if (type !== "subworkflow") {
            buttons.append(
                $("<a/>")
                    .attr({
                        "aria-label": "clone node",
                        role: "button",
                        href: "javascript:void(0)"
                    })
                    .addClass("fa-icon-button fa fa-files-o node-clone")
                    .click(e => {
                        node.clone();
                    })
            );
        }
        buttons.append(
            $("<a/>")
                .attr({
                    "aria-label": "destroy node",
                    role: "button",
                    href: "javascript:void(0)"
                })
                .addClass("fa-icon-button fa fa-times node-destroy")
                .click(e => {
                    node.destroy();
                })
        );
        // Place inside container
        $f.appendTo("#canvas-container");
        // Position in container
        var o = $("#canvas-container").position();
        var p = $("#canvas-container").parent();
        var width = $f.width();
        var height = $f.height();
        $f.css({
            left: -o.left + p.width() / 2 - width / 2,
            top: -o.top + p.height() / 2 - height / 2
        });
        buttons.appendTo($f.find(".toolFormTitle"));
        width += buttons.width() + 10;
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
});
