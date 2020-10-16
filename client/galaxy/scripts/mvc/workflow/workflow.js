/** Workflow view */
import _ from "underscore";
import $ from "jquery";
import Backbone from "backbone";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import * as mod_toastr from "libs/toastr";
import TAGS from "mvc/tag";
import WORKFLOWS from "mvc/workflow/workflow-model";
import QueryStringParsing from "utils/query-string-parsing";
import _l from "utils/localization";
import LoadingIndicator from "ui/loading-indicator";

/** View of the individual workflows */
const WorkflowItemView = Backbone.View.extend({
    tagName: "tr", // name of (orphan) root tag in this.el
    initialize: function() {
        _.bindAll(
            this,
            "render",
            "_rowTemplate",
            "renderTagEditor",
            "_templateActions",
            "removeWorkflow",
            "copyWorkflow"
        ); // every function that uses 'this' as the current object should be in here
        mod_toastr.options.timeOut = 1500;
    },

    events: {
        "click #show-in-tool-panel": "showInToolPanel",
        "click #delete-workflow": "removeWorkflow",
        "click #rename-workflow": "renameWorkflow",
        "click #copy-workflow": "copyWorkflow"
    },

    render: function() {
        $(this.el).html(this._rowTemplate());
        return this;
    },

    showInToolPanel: function() {
        // This reloads the whole page, so that the workflow appears in the tool panel.
        // Ideally we would notify only the tool panel of a change
        this.model.save(
            { show_in_tool_panel: !this.model.get("show_in_tool_panel") },
            {
                success: function() {
                    window.location = `${getAppRoot()}workflows/list`;
                }
            }
        );
    },

    removeWorkflow: function() {
        const wfName = this.model.get("name");
        if (window.confirm(`Are you sure you want to delete workflow '${wfName}'?`)) {
            this.model.destroy({
                success: function() {
                    mod_toastr.success(`Successfully deleted workflow '${wfName}'`);
                }
            });
            this.remove();
        }
    },

    renameWorkflow: function() {
        const oldName = this.model.get("name");
        const newName = window.prompt(`Enter a new Name for workflow '${oldName}'`, oldName);
        if (newName) {
            this.model.save(
                { name: newName },
                {
                    success: function() {
                        mod_toastr.success(`Successfully renamed workflow '${oldName}' to '${newName}'`);
                    }
                }
            );
            this.render();
        }
    },

    copyWorkflow: function() {
        let Galaxy = getGalaxyInstance();
        const oldName = this.model.get("name");
        $.getJSON(`${this.model.urlRoot}/${this.model.id}/download`, wfJson => {
            let newName = `Copy of ${oldName}`;
            const currentOwner = this.model.get("owner");
            if (currentOwner != Galaxy.user.attributes.username) {
                newName += ` shared by user ${currentOwner}`;
            }
            wfJson.name = newName;
            this.collection.create(wfJson, {
                at: 0,
                wait: true,
                success: function() {
                    mod_toastr.success(`Successfully copied workflow '${oldName}' to '${newName}'`);
                },
                error: function(model, resp, options) {
                    // signature seems to have changed over the course of backbone dev
                    // see https://github.com/jashkenas/backbone/issues/2606#issuecomment-19289483
                    mod_toastr.error(options.errorThrown);
                }
            });
        }).error((jqXHR, textStatus, errorThrown) => {
            mod_toastr.error(jqXHR.responseJSON.err_msg);
        });
    },

    _rowTemplate: function() {
        let Galaxy = getGalaxyInstance();
        let show = this.model.get("show_in_tool_panel");
        let wfId = this.model.id;
        const checkboxHtml = `<input id="show-in-tool-panel" type="checkbox" class="show-in-tool-panel" ${
            show ? `checked="${show}"` : ""
        } value="${wfId}">`;
        return `
            <td>
                <div class="btn-group">
                    <a href="${getAppRoot()}workflow/editor?id=${this.model.id}" class="btn btn-secondary">
                        ${_.escape(this.model.get("name"))}
                    </a>
                    <button type="button" class="btn btn-secondary dropdown-toggle dropdown-toggle-split" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                      <span class="sr-only">Toggle Dropdown</span>
                    </button>
                    ${this._templateActions()}
                </div>
            </td>
            <td>
                <div class="${wfId} tags-display">
                </div>
            </td>
            <td>
                ${this.model.get("owner") === Galaxy.user.attributes.username ? "You" : this.model.get("owner")}
            </td>
            <td>${this.model.get("number_of_steps")}</td>
            <td>${this.model.get("published") ? "Yes" : "No"}</td>
            <td>${checkboxHtml}</td>`;
    },

    renderTagEditor: function() {
        const TagEditor = new TAGS.TagsEditor({
            model: this.model,
            el: $.find(`.${this.model.id}.tags-display`),
            workflow_mode: true
        });
        TagEditor.toggle(true);
        TagEditor.render();
    },

    /** Template for user actions for workflows */
    _templateActions: function() {
        let Galaxy = getGalaxyInstance();
        if (this.model.get("owner") === Galaxy.user.attributes.username) {
            return `<div class="dropdown-menu">
                        <a class="dropdown-item" href="${getAppRoot()}workflow/editor?id=${this.model.id}">Edit</a>
                        <a class="dropdown-item" href="${getAppRoot()}workflows/run?id=${this.model.id}">Run</a>
                        <a class="dropdown-item" href="${getAppRoot()}workflow/sharing?id=${this.model.id}">Share</a>
                        <a class="dropdown-item" href="${getAppRoot()}api/workflows/${
                this.model.id
            }/download?format=json-download">Download</a>
                        <a class="dropdown-item" id="copy-workflow" style="cursor: pointer;">Copy</a>
                        <a class="dropdown-item" id="rename-workflow" style="cursor: pointer;">Rename</a>
                        <a class="dropdown-item" href="${getAppRoot()}workflow/display_by_id?id=${
                this.model.id
            }">View</a>
                        <a class="dropdown-item" id="delete-workflow" style="cursor: pointer;">Delete</a>
                    </div>`;
        } else {
            return `<ul class="dropdown-menu">
                        <li><a href="${getAppRoot()}workflow/display_by_username_and_slug?username=${this.model.get(
                "owner"
            )}&slug=${this.model.get("slug")}">View</a></li>
                        <li><a href="${getAppRoot()}workflows/run?id=${this.model.id}">Run</a></li>
                        <li><a id="copy-workflow" style="cursor: pointer;">Copy</a></li>
                        <li><a class="link-confirm-shared-${
                            this.model.id
                        }" href="${getAppRoot()}workflow/sharing?unshare_me=True&id=${this.model.id}">Remove</a></li>
                    </ul>`;
        }
    }
});

/** View of the main workflow list page */
const WorkflowListView = Backbone.View.extend({
    title: _l("Workflows"),
    active_tab: "workflow",
    initialize: function() {
        LoadingIndicator.markViewAsLoading(this);
        _.bindAll(this, "adjustActiondropdown");
        this.collection = new WORKFLOWS.WorkflowCollection();
        this.collection.fetch().done(this.render());
        this.collection.bind("add", this.appendItem);
        this.collection.on("sync", this.render, this);
    },

    events: {
        dragover: "highlightDropZone",
        dragleave: "unhighlightDropZone"
    },

    highlightDropZone: function(ev) {
        $(".hidden_description_layer").addClass("dragover");
        $(".menubutton").addClass("background-none");
        ev.preventDefault();
    },

    unhighlightDropZone: function() {
        $(".hidden_description_layer").removeClass("dragover");
        $(".menubutton").removeClass("background-none");
    },

    drop: function(e) {
        // TODO: check that file is valid galaxy workflow
        this.unhighlightDropZone();
        e.preventDefault();
        const files = e.dataTransfer.files;
        for (let i = 0, f; (f = files[i]); i++) {
            this.readWorkflowFiles(f);
        }
    },

    readWorkflowFiles: function(f) {
        const reader = new FileReader();
        reader.onload = theFile => {
            let wf_json;
            try {
                wf_json = JSON.parse(reader.result);
            } catch (e) {
                mod_toastr.error(`Could not read file '${f.name}'. Verify it is a valid Galaxy workflow`);
                wf_json = null;
            }
            if (wf_json) {
                this.collection.create(wf_json, {
                    at: 0,
                    wait: true,
                    success: function() {
                        mod_toastr.success(`Successfully imported workflow '${wf_json.name}'`);
                    },
                    error: function(model, resp, options) {
                        mod_toastr.error(options.errorThrown);
                    }
                });
            }
        };
        reader.readAsText(f, "utf-8");
    },

    _showArgErrors: _.once(() => {
        // Parse args out of params, display if there's a message.
        const msg_text = QueryStringParsing.get("message");
        const msg_status = QueryStringParsing.get("status");
        if (msg_status === "error") {
            mod_toastr.error(_.escape(msg_text || "Unknown Error, please report this to an administrator."));
        } else if (msg_text) {
            mod_toastr.info(_.escape(msg_text));
        }
    }),

    render: function() {
        // Add workflow header
        const header = this._templateHeader();
        // Add the actions buttons
        const templateActions = this._templateActionButtons();
        const tableTemplate = this._templateWorkflowTable();
        this.$el.html(header + templateActions + tableTemplate);
        _.each(this.collection.models, item => {
            // in case collection is not empty
            this.appendItem(item);
            this.confirmDelete(item);
        });
        const minQueryLength = 3;
        this.searchWorkflow(this.$(".search-wf"), this.$(".workflow-search tr"), minQueryLength);
        this.adjustActiondropdown();
        this._showArgErrors();
        this.$(".hidden_description_layer")
            .get(0)
            .addEventListener("drop", _.bind(this.drop, this));
        return this;
    },

    appendItem: function(item) {
        const workflowItemView = new WorkflowItemView({
            model: item,
            collection: this.collection
        });
        $(".workflow-search").append(workflowItemView.render().el);
        workflowItemView.renderTagEditor();
    },

    /** Add confirm box before removing/unsharing workflow */
    confirmDelete: function(workflow) {
        const $el_shared_wf_link = this.$(`.link-confirm-shared-${workflow.id}`);
        $el_shared_wf_link.click(() =>
            window.confirm(`Are you sure you want to remove the shared workflow '${workflow.attributes.name}'?`)
        );
    },

    /** Implement client side workflow search/filtering */
    searchWorkflow: function($el_searchinput, $el_tabletr, min_querylen) {
        $el_searchinput.on("keyup", function() {
            const query = $(this).val();
            // Filter when query is at least 3 characters
            // otherwise show all rows
            if (query.length >= min_querylen) {
                // Ignore the query's case using 'i'
                const regular_expression = new RegExp(query, "i");
                $el_tabletr.hide();
                $el_tabletr
                    .filter(function() {
                        // Apply regular expression on each row's text
                        // and show when there is a match
                        return regular_expression.test($(this).text());
                    })
                    .show();
            } else {
                $el_tabletr.show();
            }
        });
    },

    /** Ajust the position of dropdown with respect to table */
    adjustActiondropdown: function() {
        $(this.el).on("show.bs.dropdown", function() {
            $(this.el).css("overflow", "inherit");
        });
        $(this.el).on("hide.bs.dropdown", function() {
            $(this.el).css("overflow", "auto");
        });
    },

    /** Template for no workflow */
    _templateNoWorkflow: function() {
        return '<div class="wf-nodata"> You have no workflows. </div>';
    },

    /** Template for actions buttons */
    _templateActionButtons: function() {
        return `<ul class="manage-table-actions"><li><input class="search-wf form-control" type="text" autocomplete="off" placeholder="search for workflow..."></li><li><a class="action-button fa fa-plus wf-action" id="new-workflow" title="Create new workflow" href="${getAppRoot()}workflows/create"></a></li><li><a class="action-button fa fa-upload wf-action" id="import-workflow" title="Upload or import workflow" href="${getAppRoot()}workflows/import"></a></li></ul>`;
    },

    /** Template for workflow table */
    _templateWorkflowTable: function() {
        const tableHtml =
            '<table class="table colored"><thead>' +
            '<tr class="header">' +
            "<th>Name</th>" +
            "<th>Tags</th>" +
            "<th>Owner</th>" +
            "<th># of Steps</th>" +
            "<th>Published</th>" +
            "<th>Show in tools panel</th>" +
            "</tr></thead>";
        return `${tableHtml}<tbody class="workflow-search "><div class="hidden_description_layer"><p>Drop workflow files here to import</p></tbody></table></div>`;
    },

    /** Main template */
    _templateHeader: function() {
        return (
            '<div class="page-container">' +
            '<div class="user-workflows wf">' +
            '<div class="response-message"></div>' +
            "<h2>" +
            _l("Your workflows") +
            "</h2>" +
            "</div>" +
            "</div>"
        );
    }
});

export default {
    View: WorkflowListView
};
