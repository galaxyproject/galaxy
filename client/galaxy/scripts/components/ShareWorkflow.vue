<template>
    <div>
        <div class="page-container share-wf">
            <h2> 
              Workflow: {{ workflowItem.name }}
            </h2>
        </div>
        <ul class="manage-table-actions back-wf-list">
            <li>
                <a class='action-button' title='Back to workflows list' v-bind:href="wfListUrl"> Back to workflows list </a>
            </li>
        </ul>
        <hr>
        <div v-if="workflowItem.user_name !== ''">
            <h3>
                Share
            </h3>
            <div v-if="workflowItem.importable">
		This workflow is currently <strong>{{ shareStatus }}</strong>.
		<div>
		    Anyone can view and import this workflow by visiting the following URL:
		    <blockquote>
		        <a id="item-url" v-bind:href="workflowItem.url" target="_top">{{ workflowItem.url }}</a>
		        <span id="item-url-text" style="display: none">
		            {{ lastButOneComp }}/<span id='item-identifier'>{{ lastComp }}</span>
		        </span>
		        <a href="#" id="edit-identifier"><img src="/static/images/fugue/pencil.png"/></a>
		    </blockquote>
		    <div v-if="workflowItem.published">
		        This workflow is publicly listed and searchable in Galaxy's
		        <a v-bind:href="publishedUrl" target="_top">Published Workflows</a> section.
		    </div>
		</div>
                <div>
                    <form>
                        <div v-if="!workflowItem.published">
                            <input class="action-button submit-button" value='Disable Access to Workflow Link' name="disable_link_access"
                                v-on:click="submit">
                            <div class="toolParamHelp">Disables workflow's link so that it is not accessible.</div>
                            <br />
                            <input class="action-button submit-button" value="Publish Workflow" name="publish" v-on:click="submit">
                            <div class="toolParamHelp">Publishes the workflow to Galaxy's
                               <a v-bind:href="publishedUrl" target="_top">Published workflow</a> section, where it is publicly listed and searchable.
                            </div>
                        <br />
                        </div>
                        <div v-else>
                            <input class="action-button submit-button" value='Unpublish Workflow' name="unpublish" v-on:click="submit">
                            <div class="toolParamHelp">Removes this workflow from Galaxy's <a v-bind:href="publishedUrl" target="_top">Published Workflow</a> section so that it is not publicly listed or searchable.</div>
                            <br />
                            <input class="action-button submit-button" value='Disable Access to workflow via Link and Unpublish' name="disable_link_access_and_unpublish" v-on:click="submit">
                            <div class="toolParamHelp">Disables this workflow's link so that it is not accessible and removes it from Galaxy's
                               <a v-bind:href="publishedUrl" target='_top'>Published workflow</a>
                               section so that it is not publicly listed or searchable.
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div v-else>
                <p>This workflow is currently restricted so that only you and the users listed below can access it.</p>
                <form>
                    <input class="action-button submit-button" value="Make Workflow Accessible via Link" name="make_accessible_via_link" v-on:click="submit">
                    <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the workflow.</div>
                    <br />
                    <input class="action-button submit-button" value="Make Workflow Accessible and Publish" name="make_accessible_and_publish" v-on:click="submit">
                    <div class="toolParamHelp">
                        Makes the workflow accessible via link (see above) and publishes it to Galaxy's
                        <a v-bind:href="publishedUrl" target='_top'>Published workflow </a> section, where it is publicly listed and searchable.
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>
<script>

import axios from "axios";
import async_save_text from "utils/async-save-text";
import * as mod_toastr from "libs/toastr";

export default {
    props: {
        id: {
            type: String,
            required: true
        }
    },
    data() {
        return {
            errormessage: null,
            workflowItem: {},
            shareStatus: "",
            url: "",
            splitUrl: [],
            lastButOneComp: "",
            lastComp: "",
            publishedUrl: Galaxy.root + 'workflows/list_published',
            wfListUrl: Galaxy.root + 'workflows/list'
        }
    },
    created: function() {
        let url = Galaxy.root + 'workflow/sharing?id=' + this.id
        this.ajaxCall(url);
    },
    methods: {
        ajaxCall: function(url) {
            axios
                .get(url)
                .then(response => {
                    this.updateView(response);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        updateView: function(response) {
            this.workflowItem = response.data.workflow_item;
            this.url = this.workflowItem.url;
            if( this.workflowItem.importable === true ) {
                this.shareStatus = "accessible via link";
                if( this.workflowItem.published === true ) {
                    this.shareStatus += " and published";
                }
                this.splitUrl = this.url.split("/");
                this.lastButOneComp = this.splitUrl.splice(0, this.splitUrl.length - 1);
                this.lastButOneComp = this.lastButOneComp.join("/");
                this.lastComp = this.splitUrl.splice(-1, 1);
                this.lastComp = this.lastComp.join("/");
            }
        },
        registerAsyncCalls: function(id) {
            $(document).ready( function() {
                // Set up slug-editing functionality.
                let on_start = function( text_elt ) {
                    // Replace URL with URL text.
                    $('#item-url').hide();
                    $('#item-url-text').show();

                    // Allow only lowercase alphanumeric and '-' characters in slug.
                    text_elt.keyup(function(){
                        text_elt.val($(this).val().replace(/\s+/g,'-').replace(/[^a-zA-Z0-9\-]/g,'').toLowerCase());
                    });
                };
                let on_finish = function( text_elt ) {
                    // Replace URL text with URL.
                    $('#item-url-text').hide();
                    $('#item-url').show();
                    // Set URL to new value.
                    var new_url = $('#item-url-text').text();
                    var item_url_obj = $('#item-url');
                    item_url_obj.attr("href", new_url);
                    item_url_obj.text(new_url);
                };
                let url = Galaxy.root + "workflow/set_slug_async?id=" + id;
                async_save_text("edit-identifier", "item-identifier", url, "new_slug", null, false, 0, on_start, on_finish);
            });
        },
        getUrl: function() {
            return Galaxy.root + "workflow/sharing?id=" + this.id;
        },
        submit: function(event) {
            let url = Galaxy.root + 'workflow/sharing',
                attr = event.target.name,
                value = event.target.value;
            $.ajax({
                url: url,
                data: { id: this.id, [attr]: value },
                method: "POST"
            })
            .done(response => {
                window.location = Galaxy.root + 'workflows/share_workflow?id=' + this.id;
            })
            .fail(response => {
                this.showError(response);
            });
        }
    },
    updated: function() {
        this.registerAsyncCalls(this.id);
    }
};
</script>
<style>
    .share-wf {
        margin-top: 1%;
    }
    .submit-button {
        width: 30%;
    }
</style>
