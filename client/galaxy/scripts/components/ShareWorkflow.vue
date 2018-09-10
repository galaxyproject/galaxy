<template>
    <div>
        <div class="page-container share-wf">
            <h2>
              Workflow: {{ workflowItem.name }}
            </h2>
        </div>
        <ul class="manage-table-actions">
            <li>
                <a class="btn btn-secondary" type="button" title='Back to workflows list' :href="wfListUrl"> Back to workflows list</a>
            </li>
        </ul>
        <hr>
        <div v-if="workflowItem.user_name !== ''">
            <h3>Share</h3>
            <div v-if="workflowItem.importable">
                This workflow is currently <strong>{{ shareStatus }}</strong>.
                <a v-bind:href="'https://twitter.com/intent/tweet?text=Link%20to%20my%20Galaxy%20workflow: ' + workflowItem.url + '%20%23sciworkflows' " title="Share the workflow on Twitter" target="_blank">Share in tweet</a>
                <div class="url-section">
                    <a class="lead" id="item-url" :href="workflowItem.url" target="_blank">{{ workflowItem.url }}</a>
                    <span id="item-url-text" style="display: none">
                        {{ lastButOneComp }}/<span id='item-identifier'>{{ lastComp }}</span>
                    </span>
                    <a class="btn btn-secondary btn-sm" type="button" href="#" id="edit-identifier" title="Edit workflow url"><span class="fa fa-pencil"></span></a>
                    <span id="save-hint" style="display: none"><i>hit ENTER to save</i></span>
                </div>
                <div>

        		    <div v-if="workflowItem.published">
        		        This workflow is publicly listed and searchable in Galaxy's
        		        <a :href="publishedUrl" target="_blank">Published Workflows</a> section.
        		    </div>
        		</div>
                <div>
                    <form>
                        <div v-if="!workflowItem.published">
                            <button class="btn btn-secondary" type="button" name="disable_link_access" v-on:click="submit" title="Disable access to workflow link">Disable access
                            </button>
                            <button class="btn btn-secondary" type="button" name="publish" v-on:click="submit" title="Publish workflow and make it searchable">Publish workflow
                            </button>
                        </div>
                        <div v-else>
                            <button class="btn btn-secondary" type="button" name="unpublish" v-on:click="submit" title="Unpublish workflow">Unpublish workflow
                            </button>
                            <button class="btn btn-secondary" type="button" name="disable_link_access_and_unpublish" v-on:click="submit" title="Disable access to workflow via link and unpublish">Disable access
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            <div v-else>
                <p>This workflow is currently restricted so that only you and the users listed below can access it.</p>
                <form>
                    <button class="btn btn-secondary" type="button" name="make_accessible_via_link" v-on:click="submit" title="Make Workflow Accessible via Link"> Make Workflow Accessible via Link
                    </button>
                    <button class="btn btn-secondary" type="button" name="make_accessible_and_publish" v-on:click="submit" title="Make Workflow Accessible and Publish"">Make Workflow Accessible and Publish
                    </button>
                </form>
            </div>
            <div class="sharing-section">
                <h4>Share with users</h4>
                <div v-if="workflowItem.users_shared_with && workflowItem.users_shared_with.length > 0">
                    <p>Users in the following list will be able to see and import this workflow until they are removed.</p>
                    <table class="table table-sm table-striped colored">
                        <tr class="header">
                            <th>Email</th>
                            <th></th>
                        </tr>
                        <tr v-for="item in workflowItem.users_shared_with">
                            <td>
                                {{item.user_email}}
                            </td>
                            <td>
                                 <button class="btn btn-secondary btn-sm" type="button" v-on:click="unshareWorkflow(item.user_id)"
                                 v-bind:title="'Stop sharing with ' + item.user_email">Remove
                                 </button>
                            </td>
                        </tr>
                    </table>
                    <a class="btn btn-secondary" type="button" :href="shareWfUrl" title="Share the workflow with a different user">Share with another user</a>
                </div>
                <div v-else>
                    <p>You have not shared this workflow with any users yet.</p>
                    <a class="btn btn-secondary" type="button" :href="shareWfUrl">Share with a user</a>
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
                    <input type="submit" name="set_username" value="Set Username"/>
                </div>
           </form>
        </div>
        <div class="export-wf">
            <hr/>
            <h4>Export</h4>
            <div class="sharing-section">
                <div v-if="workflowItem.importable">
                    Use this URL to import the workflow directly into another Galaxy server
                    <div class="display-url lead">
                        {{ workflowItem.url }}/json
                    </div>
                </div>
                <div v-else>
                    This workflow must be accessible. Please use the option above to "Make Workflow Accessible and Publish" before receiving a URL for importing to another Galaxy.</a>
                </div>
            </div>
            <a class="btn btn-secondary" type="button" :href="createUsernameSlugUrl()" title="Download workflow as a file so that it can be saved or imported into another Galaxy server">Download</a>
            <a class="btn btn-secondary" type="button" :href="createSVGUrl" title="Download image of workflow in SVG format">Download as image</a>
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
    data: function() {
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
                    $("#edit-identifier").hide();
                    $("#save-hint").show();
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
                    $("#save-hint").hide();
                    $("#edit-identifier").show();
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
        }
    },
    updated: function() {
        this.registerAsyncCalls(this.id);
    }
};
</script>

<style scoped>

form.btn-secondary {
    margin-top: 1em;
}

.share-wf {
    margin-top: 1%;
}

h3 {
    margin-top: 1em;
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
td {
    vertical-align: middle;
}
.lead {
    margin-right: 1em;
}
.url-section {
    margin-bottom: 1em;

}
</style>
