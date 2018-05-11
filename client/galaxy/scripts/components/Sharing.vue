<template>
    <div v-if="ready">
        <h2>Share or Publish {{model_class}} `{{item.title}}`</h2>
        <div v-if="err_msg" class="ui-message ui-show alert alert-danger">
            {{ err_msg }}
        </div>
        </br>
        <div v-if="!has_username">
            <div>To make a {{model_class_lc}} accessible via link or publish it, you must create a public username:</div>
            <form class="form-group" @submit.prevent="setUsername()">
                <label/>
                <input class="form-control" type="text" v-model="new_username"/>
            </form>
            <button type="submit" class="btn btn-primary" @click="setUsername()">Set Username</button>
        </div>
        <div v-else>
            <br/>
            <h3>Make {{model_class}} Accessible via Link and Publish It</h3>
            <div v-if="item.importable">
                This {{model_class_lc}} is currently <strong>{{item_status}}</strong>.
                <div>
                    <p>Anyone can view and import this {{model_class_lc}} by visiting the following URL:</p>
                    <blockquote>
                        <a id="item-url" :href="item_url" target="_top">{{item_url}}</a>
                        <span id="item-url-text" style="display: none">
                            {{item_url_parts[0]}}<span id='item-identifier'>{{item_url_parts[1]}}</span>
                        </span>
                        <a href="#" id="edit-identifier"><img :src="pencil_url"/></a>
                    </blockquote>
                    <div v-if="item.published">
                        <p>This {{model_class_lc}} is publicly listed and searchable in Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section.</p>
                        <p>You can:</p>
                    </div>
                </div>
                <div v-if="!item.published">
                    <!-- Item is importable but not published. User can disable importable or publish. -->
                    <button @click="setSharing('disable_link_access')">Disable Access to {{model_class}} Link</button>
                    <div class="toolParamHelp">Disables {{model_class_lc}}'s link so that it is not accessible.</div>
                    <br/>
                    <button @click="setSharing('publish')">Publish {{model_class}}</button>
                    <div class="toolParamHelp">Publishes the {{model_class_lc}} to Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section, where it is publicly listed and searchable.</div>
                    <br/>
                </div>
                <div v-else>
                    <!-- Item is importable and published. User can unpublish or disable import and unpublish. -->
                    <button @click="setSharing('disable_link_access_and_unpublish')">Disable Access to {{model_class}} via Link and Unpublish</button>
                    <div class="toolParamHelp">Disables this {{model_class_lc}}'s link so that it is not accessible and removes {{model_class_lc}} from Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section so that it is not publicly listed or searchable.</div>
                    <br/>
                    <button @click="setSharing('unpublish')">Unpublish {{model_class}}</button>
                    <div class="toolParamHelp">Removes this {{model_class_lc}} from Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section so that it is not publicly listed or searchable.</div>
                </div>
            </div>
            <div v-else>
                <p>This {{model_class_lc}} is currently restricted so that only you and the users listed below can access it. You can:</p>
                <button @click="setSharing('make_accessible_via_link')">Make {{model_class}} Accessible via Link</button>
                <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the {{model_class_lc}}.</div>
                <br/>
                <button @click="setSharing('make_accessible_and_publish')">Make {{model_class}} Accessible and Publish</button>
                <div class="toolParamHelp">Makes the {{model_class_lc}} accessible via link (see above) and publishes the {{model_class_lc}} to Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section, where it is publicly listed and searchable.</div>
            </div>
            <br/><br/>
            <h3>Share {{model_class}} with Individual Users</h3>
            <div>
                <div v-if="item.users_shared_with && item.users_shared_with.length > 0">
                    <p>
                        The following users will see this {{model_class_lc}} in their {{model_class_lc}} list and will be able to view, import and run it.
                        <br/>
                        <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                            <tr class="header">
                                <th>Email</th>
                                <th/>
                            </tr>
                            <tr v-for="user in item.users_shared_with">
                                <td>{{user.email}}</td>
                                <td><button @click="setSharing('unshare_user', user.id)">Remove</button></td>
                            </tr>
                        </table>
                    </p>
                </div>
                <div v-else>
                    <p>You have not shared this {{model_class_lc}} with any users.</p>
                </div>
                <a id="share_with_a_user" class="action-button" :href="share_url">
                    <span>Share with a user</span>
                </a>
            </div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import async_save_text from "utils/async-save-text";
export default {
    props: {
        id: {
            type: String,
            required: true
        },
        plural_name: {
            type: String,
            required: true
        },
        model_class: {
            type: String,
            required: true
        }
    },
    computed: {
        model_class_lc() {
            return this.model_class.toLowerCase();
        },
        plural_name_lc() {
            return this.plural_name.toLowerCase();
        },
        item_status() {
            return this.item.published ? "accessible via link and published" : "accessible via link";
        },
        item_url() {
            return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${Galaxy.root}${
                this.item.username_and_slug
            }`;
        },
        item_url_parts() {
            let str = this.item_url;
            let index = str.lastIndexOf("/");
            return [str.substring(0, index + 1), str.substring(index + 1)];
        },
        published_url() {
            return `${Galaxy.root}${this.plural_name_lc}/list_published`;
        },
        share_url() {
            return `${Galaxy.root}${this.model_class_lc}/share/?id=${this.id}`;
        },
        slug_url() {
            return `${Galaxy.root}${this.model_class_lc}/set_slug_async/?id=${this.id}`;
        }
    },
    data() {
        return {
            ready: false,
            has_username: Galaxy.user.get("username"),
            new_username: "",
            err_msg: null,
            pencil_url: `${Galaxy.root}static/images/fugue/pencil.png`,
            item: {
                title: "title",
                username_and_slug: "username_and_slug",
                importable: false,
                published: false,
                users_shared_with: []
            }
        };
    },
    created: function() {
        this.getModel();
    },
    updated: function() {
        this.createSlugHandler();
    },
    methods: {
        getModel: function() {
            this.ready = false;
            axios
                .get(`${Galaxy.root}api/${this.plural_name_lc}/${this.id}/sharing`)
                .then(response => {
                    this.item = response.data;
                    this.ready = true;
                })
                .catch(error => (this.err_msg = error.response.data.err_msg));
        },
        setUsername: function() {
            axios
                .put(`${Galaxy.root}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.new_username || ""
                })
                .then(response => {
                    this.err_msg = null;
                    this.has_username = true;
                    this.getModel();
                })
                .catch(error => (this.err_msg = error.response.data.err_msg));
        },
        setSharing: function(action, user_id) {
            axios
                .post(`${Galaxy.root}api/${this.plural_name_lc}/${this.id}/sharing`, {
                    action: action,
                    user_id: user_id
                })
                .then(response => {
                    Object.assign(this.item, response.data);
                })
                .catch(error => (this.err_msg = error.response.data.err_msg));
        },
        createSlugHandler: function() {
            var on_start = function(text_elt) {
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
            var on_finish = function(text_elt) {
                // Replace URL text with URL.
                $("#item-url-text").hide();
                $("#item-url").show();

                // Set URL to new value.
                var new_url = $("#item-url-text").text();
                var item_url_obj = $("#item-url");
                item_url_obj.attr("href", new_url);
                item_url_obj.text(new_url);
            };
            async_save_text(
                "edit-identifier",
                "item-identifier",
                this.slug_url,
                "new_slug",
                null,
                false,
                0,
                on_start,
                on_finish
            );
        }
    }
};
</script>

<style>
.ui-show {
    display: block;
}
</style>
