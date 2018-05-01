<template>
    <div v-if="ready">
        <h2>Share or Publish {{item.model_class}} `{{item.name}}`</h2>
        <div v-if="!has_username">
            <div>To make a {{item_model_class_lc}} accessible via link or publish it, you must create a public username:</div>
            <div v-if="err_msg" class="ui-message ui-show alert alert-danger">
                {{ err_msg }}
            </div>
            <form class="form-group">
                <label/>
                <input class="form-control" type="text" v-model="username"/>
            </form>
            <button type="submit" class="btn btn-primary" @click="setUsername()">Set Username</button>
        </div>
        <div v-else>
            <br/><br/>
            <h3>Make {{item.model_class}} Accessible via Link and Publish It</h3>
            <div v-if="item.importable">
                This {{item_model_class_lc}} is currently <strong>{{item_status}}</strong>.
                <div>
                    <p>Anyone can view and import this {{item_model_class_lc}} by visiting the following URL:</p>
                    <blockquote>
                        <a id="item-url" :href="item_url" target="_top">{{item_url}}</a>
                    </blockquote>
                    <div v-if="item.published">
                        <p>This {{item_model_class_lc}} is publicly listed and searchable in Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section.</p>
                        <p>You can:</p>
                    </div>
                </div>
                <div v-if="!item.published">
                    <!-- Item is importable but not published. User can disable importable or publish. -->
                    <button @click="disableLink">Disable Access to {{item.model_class}} Link</button>
                    <div class="toolParamHelp">Disables {{item_model_class_lc}}'s link so that it is not accessible.</div>
                    <br/>
                    <button @click="enablePublish">Publish {{item.model_class}}</button>
                    <div class="toolParamHelp">Publishes the {{item_model_class_lc}} to Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section, where it is publicly listed and searchable.</div>
                    <br/>
                </div>
                <div v-else>
                    <!-- Item is importable and published. User can unpublish or disable import and unpublish. -->
                    <button @click="disablePublish">Unpublish {{item.model_class}}</button>
                    <div class="toolParamHelp">Removes this {{item_model_class_lc}} from Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section so that it is not publicly listed or searchable.</div>
                    <br/>
                    <button @click="disableLinkPublish">Disable Access to {{item.model_class}} via Link and Unpublish</button>
                    <div class="toolParamHelp">Disables this {{item_model_class_lc}}'s link so that it is not accessible and removes {{item_model_class_lc}} from Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section so that it is not publicly listed or searchable.</div>
                </div>
            </div>
            <div v-else>
                <p>This {{item_model_class_lc}} is currently restricted so that only you and the users listed below can access it. You can:</p>
                <button @click="enableLink">Make {{item.model_class}} Accessible via Link</button>
                <div class="toolParamHelp">Generates a web link that you can share with other people so that they can view and import the {{item_model_class_lc}}.</div>
                <br/>
                <button @click="enableLinkPublish">Make {{item.model_class}} Accessible and Publish</button>
                <div class="toolParamHelp">Makes the {{item_model_class_lc}} accessible via link (see above) and publishes the {{item_model_class_lc}} to Galaxy's <a :href="published_url" target="_top">Published {{plural_name}}</a> section, where it is publicly listed and searchable.</div>
            </div>
            <br/><br/>
            <h3>Share {{item.model_class}} with Individual Users</h3>
            <div>
                <div v-if="item.users_shared_with && item.users_shared_with.length > 0">
                    <p>
                        The following users will see this {{item_model_class_lc}} in their {{item_model_class_lc}} list and will be able to view, import and run it.
                        <br/>
                        <table class="colored" border="0" cellspacing="0" cellpadding="0" width="100%">
                            <tr class="header">
                                <th>Email</th>
                                <th/>
                            </tr>
                            <tr v-for="user in item.users_shared_with">
                                <td>{{user.email}}</td>
                                <td><button>Remove</button></td>
                            </tr>
                        </table>
                    </p>
                </div>
                <div v-else>
                    <p>You have not shared this {{item_model_class_lc}} with any users.</p>
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
export default {
    props: {
        id: {
            type: String,
            required: true
        },
        list_controller: {
            type: String,
            required: true
        },
        item_controller: {
            type: String,
            required: true
        },
        plural_name: {
            type: String,
            required: true
        }
    },
    computed: {
        item_model_class_lc() {
            return this.item.model_class.toLowerCase();
        },
        item_status() {
            return this.item.published ? "accessible via link" : "accessible via link and published";
        },
        item_url() {
            return `${Galaxy.root}${this.item_controller}/display_by_username_and_slug/?username=${this.username}&slug=${this.item.slug}&qualified=true`;
        },
        published_url() {
            return `${Galaxy.root}${this.list_controller}/list_published`;
        },
        share_url() {
            return `${Galaxy.root}${this.item_controller}/share/?id=${this.id}`;
        }
    },
    data() {
        return {
            ready: false,
            item : {
                name: "name",
                model_class: "model_class",
                importable: true,
                published: true,
                users_shared_with: [],
                slug: "slug",
            },
            username: "",
            has_username: true,
            err_msg: null,
            user: Galaxy.user
        };
    },
    created: function() {
        axios
            .get(`${Galaxy.root}api/${this.list_controller}/${this.id}`)
            .then(response => {
                this.item = response.data;
                this.ready = true;
            })
            .catch(error => this.err_msg = error.response.data.err_msg)
    },
    methods: {
        setUsername: function() {
            axios
                .put(`${Galaxy.root}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.username
                })
                .then(response => this.has_username = true)
                .catch(error => this.err_msg = error.response.data.err_msg);
        },
        enableLink: function() {
        },
        disableLink: function() {
        },
        enablePublish: function() {
        },
        disablePublish: function() {
        },
        enableLinkPublish: function() {
        },
        disableLinkPublish: function() {
        }
    },
    updated: function() {
    }
};
</script>

<style>
.ui-show {
    display: block;
}
</style>
