<template>
    <div>
        <div class="page-container share-wf">
            <h4>
              Workflow: {{ workflowItem.name }}
            </h4>
        </div>
        <ul class="manage-table-actions">
            <li>
                <a class="action-button" :href="createUsernameSlugUrl()" title="Download workflow as a file so that it can be saved or imported into another Galaxy server">Download</a>
            </li>
            <li>
                <a class="action-button" v-on:click.prevent="createWorkflowSVG" title="Create image of workflow in SVG format">Create image</a>
            </li>
            <li>
                <a class='action-button' title='Back to workflows list' :href="wfListUrl"> Back to workflows list </a>
            </li>
        </ul>
        <hr>
        <div v-if="workflowItem.user_name !== ''">
            <h4>
                Share
            </h4>
            <div v-if="workflowItem.importable">
		        This workflow is currently <strong>{{ shareStatus }}</strong>.
		        <div>
		            Anyone can view and import this workflow by visiting the following URL:
        		    <blockquote>
        		        <a id="item-url" :href="workflowItem.url" target="_top">{{ workflowItem.url }}</a>
        		        <span id="item-url-text" style="display: none">
        		            {{ lastButOneComp }}/<span id='item-identifier'>{{ lastComp }}</span>
        		        </span>
        		        <a href="#" id="edit-identifier" title="Edit workflow url"><img src="/static/images/fugue/pencil.png"/></a>
        		    </blockquote>
        		    <div v-if="workflowItem.published">
        		        This workflow is publicly listed and searchable in Galaxy's
        		        <a :href="publishedUrl" target="_top">Published Workflows</a> section.
        		    </div>
        		</div>
                <div>
                    <form>
                        <div v-if="!workflowItem.published">
                            <input class="action-button submit-button" value='Disable Access to Workflow Link' name="disable_link_access"
                                v-on:click="submit" title="Disable Access to Workflow Link">
                            <div class="toolParamHelp">Disables workflow's link so that it is not accessible.</div>
                            <br />
                            <input class="action-button submit-button" value="Publish Workflow" name="publish" v-on:click="submit" title="Publish Workflow">
                            <div class="toolParamHelp">Publishes the workflow to Galaxy's
                               <a :href="publishedUrl" target="_top">Published workflow</a> section, where it is publicly listed and searchable.
                            </div>
                        <br />
                        </div>
                        <div v-else>
                            <input class="action-button submit-button" value='Unpublish Workflow' name="unpublish" v-on:click="submit" title="Unpublish Workflow">
                            <div class="toolParamHelp">Removes this workflow from Galaxy's <a :href="publishedUrl" target="_top">Published Workflow</a> section so that it is not publicly listed or searchable.</div>
                            <br />
                            <input class="action-button submit-button" value='Disable Access and Unpublish' name="disable_link_access_and_unpublish" v-on:click="submit" title="Disable Access to workflow via Link and Unpublish">
                            <div class="toolParamHelp">Disables this workflow's link so that it is not accessible and removes it from Galaxy's
                               <a :href="publishedUrl" target='_top'>Published workflow</a>
                               section so that it is not publicly listed or searchable.
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            <div v-else>
                <p>This workflow is currently restricted so that only you and the users listed below can access it.</p>
                <form>
                    <input class="action-button submit-button" value="Make Workflow Accessible via Link" name="make_accessible_via_link" v-on:click="submit" title="Make Workflow Accessible via Link">
                    <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the workflow.</div>
                    <br />
                    <input class="action-button submit-button" value="Make Workflow Accessible and Publish" name="make_accessible_and_publish"
                        v-on:click="submit" title="Make Workflow Accessible and Publish"">
                    <div class="toolParamHelp">
                        Makes the workflow accessible via link (see above) and publishes it to Galaxy's
                        <a :href="publishedUrl" target='_top'>Published workflow </a> section, where it is publicly listed and searchable.
                    </div>
                </form>
            </div>
            <div class="sharing-section">
                <h5>Share workflow with users</h5>
                <div v-if="workflowItem.users_shared_with && workflowItem.users_shared_with.length > 0">
                    <p>The following users will see this workflow in their workflow list and will be able to view, import, and run it.</p>
                    <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                        <tr class="header">
                            <th>Email</th>
                            <th></th>
                        </tr>
                        <tr v-for="item in workflowItem.users_shared_with">
                            <td>
                                <div>{{item.user_email}}</div>
                            </td>
                            <td>
                                <div>
                                     <input class="action-button submit-button" value="Unshare" v-on:click="unshareWorkflow(item.user_id)" title="Unshare workflow with the user">
                                </div>
                            </td>
                        </tr>
                    </table>
                    <a class="action-button" :href="shareWfUrl" title="Share the workflow with a different user"><span>Share with another user</span></a>
                </div>
                <div v-else>
                    <p>You have not shared this workflow with any users yet.</p>
                    <a class="action-button" :href="shareWfUrl"><span>Share with a user</span></a>
                </div>
            </div>
            <div v-if="workflowItem.importable" class="sharing-section">
                <h5>Share workflow on social media</h5>
                <social-sharing :url="workflowUrl"
                                title="Link to a Galaxy workflow: "
                                quote="Galaxy workflow"
                                hashtags="sciworkflows"
                                inline-template>
                    <div class="share-link">
                        <network network="twitter" id="twitter" class="social-link"><i class="fa fa-fw fa-twitter"></i> Twitter </network>
                        <network network="facebook" id="facebook" class="social-link"><i class="fa fa-fw fa-facebook"></i> Facebook </network>
                        <network network="googleplus" id="googleplus" class="social-link"><i class="fa fa-fw fa-google-plus"></i> Google+ </network>
                        <network network="linkedin" id="linkedin" class="social-link"><i class="fa fa-fw fa-linkedin"></i> LinkedIn </network>
                    </div>
                </social-sharing>
            </div>
        </div>
        <div v-else>
            <p>To make a workflow accessible via link or publish it, you must create a public username:</p>
            <form :action="createPublicNameUrl" method="POST">
                <div class="form-row">
                    <label>Public Username:</label>
                    <div class="form-row-input">
                        <input type="text" name="username" size="40"/>
                        <input type="hidden" name="share_wf" value="share_wf"/>
                    </div>
                </div>
                <div style="clear: both"></div>
                <div class="form-row">
                    <input class="action-button" type="submit" name="set_username" value="Set Username"/>
                </div>
           </form>
        </div>
        <div class="export-wf">
            <hr/>
            <h4>Export</h4>
            <div class="sharing-section">
                <div v-if="workflowItem.importable">
                    Use this URL to import the workflow directly into another Galaxy server:
                    <div class="display-url">
                        {{ workflowItem.url }}/json
                    </div>
                   (Copy this URL into the box titled 'Workflow URL' in the Import Workflow page.)
                </div>
                <div v-else>
                    This workflow must be accessible. Please use the option above to "Make Workflow Accessible and Publish" before receiving a URL for importing to another Galaxy.</a>
                </div>
            </div>
            <div class="sharing-section">
                <span>Export to the <a href="http://www.myexperiment.org/" target="_blank">www.myexperiment.org</a> site.</span>
                <form :action="createMyExperimentUrl" method="POST">
                <div class="form-row">
                    <label>myExperiment username:</label>
                    <input type="text" name="myexp_username" value="" size="25" placeholder="username" autocomplete="off"/>
                </div>
                <div class="form-row">
                    <label>myExperiment password:</label>
                    <input type="password" name="myexp_password" value="" size="25" placeholder="password" autocomplete="off"/>
                </div>
                <div class="form-row">
                    <input type="submit" value="Export to myExperiment"/>
                </div>
            </form>
            </div>
        </div>
    </div>
</template>
<script>
import Vue from "vue";
import axios from "axios";
import async_save_text from "utils/async-save-text";
import * as mod_toastr from "libs/toastr";
import SocialSharing from "vue-social-sharing";

export default {
    props: {
        id: {
            type: String,
            required: true
        },
        status: {
            type: String,
            required: false
        },
        message: {
            type: String,
            required: false
        }
    },
    data() {
        return {
            errormessage: null,
            workflowItem: {},
            shareStatus: "",
            workflowUrl: "",
            splitUrl: [],
            lastButOneComp: "",
            lastComp: "",
            publishedUrl: Galaxy.root + "workflows/list_published",
            wfListUrl: Galaxy.root + "workflows/list",
            shareWfUrl: Galaxy.root + "workflow/share?id=" + this.id,
            createSVGUrl: Galaxy.root + "workflow/gen_image?id=" + this.id,
            createMyExperimentUrl: Galaxy.root + "workflow/export_to_myexp?id=" + this.id,
            createPublicNameUrl: Galaxy.root + "workflow/set_public_username?id=" + this.id
        };
    },
    created: function() {
        let url = Galaxy.root + "api/workflows/sharing?id=" + this.id;
        if (this.message !== "" && this.status === "error") {
            this.showError(this.message);
        }
        this.ajaxCall(url);
    },
    methods: {
        ajaxCall: function(url) {
            axios
                .get(url)
                .then(response => {
                    this.updateView(response);
                    Vue.use(SocialSharing);
                })
                .catch(e => {
                    this.showError(e);
                });
        },
        showError: function(errorMsg) {
            mod_toastr.error(errorMsg);
        },
        updateView: function(response) {
            this.workflowItem = response.data;
            this.workflowUrl = this.workflowItem.url;
            if (this.workflowItem.importable === true) {
                this.shareStatus = "accessible via link";
                if (this.workflowItem.published === true) {
                    this.shareStatus += " and published";
                }
                this.splitUrl = this.workflowUrl.split("/");
                this.lastButOneComp = this.splitUrl.splice(0, this.splitUrl.length - 1);
                this.lastButOneComp = this.lastButOneComp.join("/");
                this.lastComp = this.splitUrl.splice(-1, 1);
                this.lastComp = this.lastComp.join("/");
            }
        },
        registerAsyncCalls: function(id) {
            $(document).ready(function() {
                // Set up slug-editing functionality.
                let on_start = function(text_elt) {
                    // Replace URL with URL text.
                    $("#item-url").hide();
                    $("#item-url-text").show();
                    // Allow only lowercase alphanumeric and '-' characters in slug.
                    text_elt.keyup(function() {
                        text_elt.val(
                            $(this)
                                .val()
                                .replace(/\s+/g, "-")
                                .replace(/[^a-zA-Z0-9\-]/g, "")
                                .toLowerCase()
                        );
                    });
                };
                let on_finish = function(text_elt) {
                    // Replace URL text with URL.
                    $("#item-url-text").hide();
                    $("#item-url").show();
                    // Set URL to new value.
                    var new_url = $("#item-url-text").text();
                    var item_url_obj = $("#item-url");
                    item_url_obj.attr("href", new_url);
                    item_url_obj.text(new_url);
                };
                let url = Galaxy.root + "workflow/set_slug_async?id=" + id;
                async_save_text(
                    "edit-identifier",
                    "item-identifier",
                    url,
                    "new_slug",
                    null,
                    false,
                    0,
                    on_start,
                    on_finish
                );
            });
        },
        getUrl: function() {
            return Galaxy.root + "api/workflows/sharing?id=" + this.id;
        },
        submit: function(event) {
            let url = Galaxy.root + "api/workflows/sharing",
                attr = event.target.name,
                value = event.target.value;
            $.ajax({
                url: url,
                data: { id: this.id, [attr]: value },
                method: "GET"
            })
                .done(response => {
                    window.location = Galaxy.root + "workflows/sharing?id=" + this.id;
                })
                .fail(response => {
                    this.showError(response);
                });
        },
        unshareWorkflow: function(userId) {
            let url = Galaxy.root + "api/workflows/sharing?id=" + this.id + "&unshare_user=" + userId;
            this.ajaxCall(url);
        },
        createUsernameSlugUrl: function() {
            return this.workflowItem.url + "/json-download";
        },
        createWorkflowSVG: function() {
            let url = this.createSVGUrl;
            axios
                .get(url)
                .then(response => {
                    window.location = url;
                })
                .catch(e => {
                    this.showError(
                        "Galaxy is unable to create the SVG image. Please check your workflow, there might be missing tools."
                    );
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
    width: 32%;
}

h3 {
    margin-top: 1em;
}

input.action-button {
    margin-left: 0;
}

a.action-button {
    margin-top: 0.5%;
}

.display-url {
    margin: 0.5em 0em 0.5em 0.5em;
    font-weight: bold;
}

.sharing-section {
    margin-top: 1em;
}

.share-link {
    cursor: pointer;
}

.social-link {
    margin-right: 0.5%;
}
</style>
