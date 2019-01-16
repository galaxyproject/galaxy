<template>
    <div v-if="ready">
        <h2>Share or Publish {{ model_class }} `{{ item.title }}`</h2>
        <b-alert :show="show_danger" variant="danger" dismissible> {{ err_msg }} </b-alert>
        <br />
        <div v-if="!has_username">
            <div>
                To make a {{ model_class_lc }} accessible via link or publish it, you must create a public username:
            </div>
            <form class="form-group" @submit.prevent="setUsername()">
                <label /> <input class="form-control" type="text" v-model="new_username" />
            </form>
            <b-button type="submit" variant="primary" @click="setUsername()">Set Username</b-button>
        </div>
        <div v-else>
            <br />
            <h3>Make {{ model_class }} Accessible via Link and Publish It</h3>
            <div v-if="item.importable">
                This {{ model_class_lc }} is currently <strong>{{ item_status }}</strong
                >.
                <div>
                    <p>Anyone can view and import this {{ model_class_lc }} by visiting the following URL:</p>
                    <blockquote>
                        <a id="item-url" :href="item_url" target="_top">{{ item_url }}</a>
                        <span id="item-url-text" style="display: none">
                            {{ item_url_parts[0] }}<span id="item-identifier">{{ item_url_parts[1] }}</span>
                        </span>
                        <a href="#" id="edit-identifier"><img :src="pencil_url"/></a>
                    </blockquote>
                    <div v-if="item.published">
                        <p>
                            This {{ model_class_lc }} is publicly listed and searchable in Galaxy's
                            <a :href="published_url" target="_top">Published {{ plural_name }}</a> section.
                        </p>
                        <p>You can:</p>
                    </div>
                </div>
                <div v-if="!item.published">
                    <!-- Item is importable but not published. User can disable importable or publish. -->
                    <b-button @click="setSharing('disable_link_access')"
                        >Disable Access to {{ model_class }} Link</b-button
                    >
                    <div class="toolParamHelp">Disables {{ model_class_lc }}'s link so that it is not accessible.</div>
                    <br />
                    <b-button id="make_accessible_and_publish" @click="setSharing('publish')"
                        >Publish {{ model_class }}</b-button
                    >
                    <div class="toolParamHelp">
                        Publishes the {{ model_class_lc }} to Galaxy's
                        <a :href="published_url" target="_top">Published {{ plural_name }}</a> section, where it is
                        publicly listed and searchable.
                    </div>
                    <br />
                </div>
                <div v-else>
                    <!-- Item is importable and published. User can unpublish or disable import and unpublish. -->
                    <b-button
                        id="disable_link_access_and_unpublish"
                        @click="setSharing('disable_link_access_and_unpublish')"
                        >Disable Access to {{ model_class }} via Link and Unpublish</b-button
                    >
                    <div class="toolParamHelp">
                        Disables this {{ model_class_lc }}'s link so that it is not accessible and removes
                        {{ model_class_lc }} from Galaxy's
                        <a :href="published_url" target="_top">Published {{ plural_name }}</a> section so that it is not
                        publicly listed or searchable.
                    </div>
                    <br />
                    <b-button @click="setSharing('unpublish')">Unpublish {{ model_class }}</b-button>
                    <div class="toolParamHelp">
                        Removes this {{ model_class_lc }} from Galaxy's
                        <a :href="published_url" target="_top">Published {{ plural_name }}</a> section so that it is not
                        publicly listed or searchable.
                    </div>
                </div>
            </div>
            <div v-else>
                <p>
                    This {{ model_class_lc }} is currently restricted so that only you and the users listed below can
                    access it. You can:
                </p>
                <b-button @click="setSharing('make_accessible_via_link')"
                    >Make {{ model_class }} Accessible via Link</b-button
                >
                <p v-if="has_possible_members" class="mt-2">
                    Also make all objects within the {{ model_class }} accessible.
                    <input type="checkbox" v-model="make_members_public" id="chk_make_members_public" />
                </p>
                <div class="toolParamHelp">
                    Generates a web link that you can share with other people so that they can view and import the
                    {{ model_class_lc }}.
                </div>
                <br />
                <b-button id="make_accessible_and_publish" @click="setSharing('make_accessible_and_publish')"
                    >Make {{ model_class }} Accessible and Publish</b-button
                >
                <p v-if="has_possible_members" class="mt-2">
                    Also make all objects within the {{ model_class }} accessible.
                    <input type="checkbox" v-model="make_members_public" id="chk_make_members_public" />
                </p>
                <div class="toolParamHelp">
                    Makes the {{ model_class_lc }} accessible via link (see above) and publishes the
                    {{ model_class_lc }} to Galaxy's
                    <a :href="published_url" target="_top">Published {{ plural_name }}</a> section, where it is publicly
                    listed and searchable.
                </div>
            </div>
            <br /><br />
            <h3>Share {{ model_class }} with Individual Users</h3>
            <div>
                <div v-if="item.users_shared_with && item.users_shared_with.length > 0">
                    <b-table small caption-top :fields="share_fields" :items="item.users_shared_with">
                        <template slot="table-caption">
                            The following users will see this {{ model_class_lc }} in their {{ model_class_lc }} list
                            and will be able to view, import and run it.
                        </template>
                        <template slot="id" slot-scope="cell">
                            <b-button
                                class="unshare_user"
                                size="sm"
                                @click.stop="setSharing('unshare_user', cell.value)"
                                >Remove</b-button
                            >
                        </template>
                    </b-table>
                </div>
                <div v-else>
                    <p>You have not shared this {{ model_class_lc }} with any users.</p>
                </div>
                <b-button :href="share_url" id="share_with_a_user"> <span>Share with a user</span> </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";
import async_save_text from "utils/async-save-text";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

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
            return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${getAppRoot()}${
                this.item.username_and_slug
            }`;
        },
        item_url_parts() {
            let str = this.item_url;
            let index = str.lastIndexOf("/");
            return [str.substring(0, index + 1), str.substring(index + 1)];
        },
        published_url() {
            return `${getAppRoot()}${this.plural_name_lc}/list_published`;
        },
        share_url() {
            return `${getAppRoot()}${this.model_class_lc}/share/?id=${this.id}`;
        },
        slug_url() {
            return `${getAppRoot()}${this.model_class_lc}/set_slug_async/?id=${this.id}`;
        },
        has_possible_members() {
            return ["history"].indexOf(this.model_class_lc) > -1;
        },
        show_danger() {
            return this.err_msg !== null;
        }
    },
    data() {
        let Galaxy = getGalaxyInstance();
        return {
            ready: false,
            has_username: Galaxy.user.get("username"),
            new_username: "",
            err_msg: null,
            pencil_url: `${getAppRoot()}static/images/fugue/pencil.png`,
            item: {
                title: "title",
                username_and_slug: "username_and_slug",
                importable: false,
                published: false,
                users_shared_with: []
            },
            share_fields: ["email", { key: "id", label: "" }],
            make_members_public: false
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
                .get(`${getAppRoot()}api/${this.plural_name_lc}/${this.id}/sharing`)
                .then(response => {
                    this.item = response.data;
                    this.ready = true;
                })
                .catch(error => (this.err_msg = error.response.data.err_msg));
        },
        setUsername: function() {
            let Galaxy = getGalaxyInstance();
            axios
                .put(`${getAppRoot()}api/users/${Galaxy.user.id}/information/inputs`, {
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
            let data = {
                action: action,
                user_id: user_id
            };
            if (this.has_possible_members) {
                data.make_members_public = this.make_members_public;
            }
            axios
                .post(`${getAppRoot()}api/${this.plural_name_lc}/${this.id}/sharing`, data)
                .then(response => {
                    Object.assign(this.item, response.data);
                    if (response.data.skipped) {
                        this.err_msg = "Some of the items within this object were not published due to an error.";
                    }
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
                            .replace(/[^a-zA-Z0-9-]/g, "")
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
