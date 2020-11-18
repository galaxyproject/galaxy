<template>
    <div v-if="ready">
        <h2>Share or Publish {{ model_class }} `{{ item.title }}`</h2>
        <b-alert :show="showDanger" variant="danger" dismissible> {{ err_msg }} </b-alert>
        <br />
        <div v-if="!has_username">
            <div>
                To make a {{ modelClassLower }} accessible via link or publish it, you must create a public username:
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
                This {{ modelClassLower }} is currently <strong>{{ itemStatus }}</strong
                >.
                <div>
                    <p>Anyone can view and import this {{ modelClassLower }} by visiting the following URL:</p>
                    <blockquote>
                        <font-awesome-icon role="button" icon="edit" title="Edit URL" @click="onEdit" />
                        <font-awesome-icon role="button" :icon="['far', 'clipboard']" class="ml-1" @click="onCopy" />
                        <a v-if="showUrl" id="item-url" :href="itemUrl" target="_top" class="ml-2">{{ itemUrl }}</a>
                        <span v-else id="item-url-text">
                            {{ itemUrlParts[0] }}<SlugInput class="ml-1" :slug="itemUrlParts[1]" @onChange="onChange" />
                        </span>
                    </blockquote>
                    <div v-if="item.published">
                        <p>
                            This {{ modelClassLower }} is publicly listed and searchable in Galaxy's
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
                    <div class="toolParamHelp">Disables {{ modelClassLower }}'s link so that it is not accessible.</div>
                    <br />
                    <b-button id="make_accessible_and_publish" @click="setSharing('publish')"
                        >Publish {{ model_class }}</b-button
                    >
                    <div class="toolParamHelp">
                        Publishes the {{ modelClassLower }} to Galaxy's
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
                        Disables this {{ modelClassLower }}'s link so that it is not accessible and removes
                        {{ modelClassLower }} from Galaxy's
                        <a :href="published_url" target="_top">Published {{ plural_name }}</a> section so that it is not
                        publicly listed or searchable.
                    </div>
                    <br />
                    <b-button @click="setSharing('unpublish')">Unpublish {{ model_class }}</b-button>
                    <div class="toolParamHelp">
                        Removes this {{ modelClassLower }} from Galaxy's
                        <a :href="published_url" target="_top">Published {{ plural_name }}</a> section so that it is not
                        publicly listed or searchable.
                    </div>
                </div>
            </div>
            <div v-else>
                <p>
                    This {{ modelClassLower }} is currently restricted so that only you and the users listed below can
                    access it. You can:
                </p>
                <b-button @click="setSharing('make_accessible_via_link')"
                    >Make {{ model_class }} Accessible via Link</b-button
                >
                <p v-if="hasPossibleMembers" class="mt-2">
                    Also make all objects within the {{ model_class }} accessible.
                    <input type="checkbox" v-model="make_members_public" id="chk_make_members_public" />
                </p>
                <div class="toolParamHelp">
                    Generates a web link that you can share with other people so that they can view and import the
                    {{ modelClassLower }}.
                </div>
                <br />
                <b-button id="make_accessible_and_publish" @click="setSharing('make_accessible_and_publish')"
                    >Make {{ model_class }} Accessible and Publish</b-button
                >
                <p v-if="hasPossibleMembers" class="mt-2">
                    Also make all objects within the {{ model_class }} accessible.
                    <input type="checkbox" v-model="make_members_public" id="chk_make_members_public" />
                </p>
                <div class="toolParamHelp">
                    Makes the {{ modelClassLower }} accessible via link (see above) and publishes the
                    {{ modelClassLower }} to Galaxy's
                    <a :href="published_url" target="_top">Published {{ plural_name }}</a> section, where it is publicly
                    listed and searchable.
                </div>
            </div>
            <br /><br />
            <h3>Share {{ model_class }} with Individual Users</h3>
            <div>
                <div v-if="item.users_shared_with && item.users_shared_with.length > 0">
                    <b-table small caption-top :fields="share_fields" :items="item.users_shared_with">
                        <template v-slot:table-caption>
                            The following users will see this {{ modelClassLower }} in their {{ modelClassLower }} list
                            and will be able to view, import and run it.
                        </template>
                        <template v-slot:cell(id)="cell">
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
                    <p>You have not shared this {{ modelClassLower }} with any users.</p>
                </div>
                <b-button :href="shareUrl" id="share_with_a_user"> <span>Share with a user</span> </b-button>
            </div>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClipboard, faEdit } from "@fortawesome/free-regular-svg-icons";
import SlugInput from "components/Common/SlugInput";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import axios from "axios";

Vue.use(BootstrapVue);

library.add(faClipboard);
library.add(faEdit);

export default {
    components: {
        FontAwesomeIcon,
        SlugInput,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        plural_name: {
            type: String,
            required: true,
        },
        model_class: {
            type: String,
            required: true,
        },
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            ready: false,
            has_username: Galaxy.user.get("username"),
            new_username: "",
            err_msg: null,
            item: {
                title: "title",
                username_and_slug: "username_and_slug",
                importable: false,
                published: false,
                users_shared_with: [],
            },
            share_fields: ["email", { key: "id", label: "" }],
            make_members_public: false,
            showUrl: true,
        };
    },
    computed: {
        modelClassLower() {
            return this.model_class.toLowerCase();
        },
        pluralNameLower() {
            return this.plural_name.toLowerCase();
        },
        itemStatus() {
            return this.item.published ? "accessible via link and published" : "accessible via link";
        },
        itemUrl() {
            const port = window.location.port ? `:${window.location.port}` : "";
            return `${window.location.protocol}//${window.location.hostname}${port}${getAppRoot()}${
                this.item.username_and_slug
            }`;
        },
        itemSlugParts() {
            const str = this.item.username_and_slug;
            const index = str.lastIndexOf("/");
            return [str.substring(0, index + 1), str.substring(index + 1)];
        },
        itemUrlParts() {
            const str = this.itemUrl;
            const index = str.lastIndexOf("/");
            return [str.substring(0, index + 1), str.substring(index + 1)];
        },
        published_url() {
            return `${getAppRoot()}${this.pluralNameLower}/list_published`;
        },
        shareUrl() {
            return `${getAppRoot()}${this.modelClassLower}/share/?id=${this.id}`;
        },
        slugUrl() {
            return `${getAppRoot()}${this.modelClassLower}/set_slug_async/?id=${this.id}`;
        },
        hasPossibleMembers() {
            return ["history"].indexOf(this.modelClassLower) > -1;
        },
        showDanger() {
            return this.err_msg !== null;
        },
    },
    created: function () {
        this.getModel();
    },
    methods: {
        onCopy() {
            alert("Copy");
        },
        onEdit() {
            this.showUrl = false;
        },
        onChange(newSlug) {
            this.showUrl = true;
            this.item.username_and_slug = `${this.itemSlugParts[0]}${newSlug}`;
            const requestUrl = `${this.slugUrl}&new_slug=${newSlug}`;
            axios.get(requestUrl).catch((error) => (this.err_msg = error.response.data.err_msg));
        },
        getModel() {
            this.ready = false;
            axios
                .get(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`)
                .then((response) => {
                    this.item = response.data;
                    this.ready = true;
                })
                .catch((error) => (this.err_msg = error.response.data.err_msg));
        },
        setUsername() {
            const Galaxy = getGalaxyInstance();
            axios
                .put(`${getAppRoot()}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.new_username || "",
                })
                .then((response) => {
                    this.err_msg = null;
                    this.has_username = true;
                    this.getModel();
                })
                .catch((error) => (this.err_msg = error.response.data.err_msg));
        },
        setSharing(action, user_id) {
            const data = {
                action: action,
                user_id: user_id,
            };
            if (this.hasPossibleMembers) {
                data.make_members_public = this.make_members_public;
            }
            axios
                .post(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`, data)
                .then((response) => {
                    Object.assign(this.item, response.data);
                    if (response.data.skipped) {
                        this.err_msg = "Some of the items within this object were not published due to an error.";
                    }
                })
                .catch((error) => (this.err_msg = error.response.data.err_msg));
        },
    },
};
</script>
