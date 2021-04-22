<template>
    <div v-if="ready">
        <h3>Share or Publish {{ model_class }} `{{ item.title }}`</h3>
        <b-alert :show="showDanger" variant="danger" dismissible> {{ errMsg }} </b-alert>
        <br />
        <div v-if="!hasUsername">
            <div>To make a {{ model_class }} accessible via link or publish it, you must create a public username:</div>
            <form class="form-group" @submit.prevent="setUsername()">
                <input class="form-control" type="text" v-model="newUsername" />
            </form>
            <b-button type="submit" variant="primary" @click="setUsername()">Set Username</b-button>
        </div>
        <div v-else>
            <b-form-checkbox switch class="make-accessible" v-model="item.importable" @change="onImportable">
                Make {{ model_class }} accessible
            </b-form-checkbox>
            <b-form-checkbox
                v-if="item.importable"
                class="make-publishable"
                switch
                v-model="item.published"
                @change="onPublish"
            >
                Make {{ model_class }} publicly available in
                <a :href="published_url" target="_top">Published {{ plural_name }}</a>
            </b-form-checkbox>
            <br />
            <div v-if="item.importable">
                <div>
                    This {{ model_class }} is currently <strong>{{ itemStatus }}</strong
                    >.
                </div>
                <p>Anyone can view and import this {{ model_class }} by visiting the following URL:</p>
                <blockquote>
                    <b-button title="Edit URL" @click="onEdit" v-b-tooltip.hover variant="link" size="sm">
                        <font-awesome-icon icon="edit" />
                    </b-button>
                    <b-button id="tooltip-clipboard" @click="onCopy" @mouseout="onCopyOut" variant="link" size="sm">
                        <font-awesome-icon icon="link" />
                    </b-button>
                    <b-tooltip target="tooltip-clipboard" triggers="hover">
                        {{ tooltipClipboard }}
                    </b-tooltip>
                    <a v-if="showUrl" id="item-url" :href="itemUrl" target="_top" class="ml-2">
                        url:
                        {{ itemUrl }}
                    </a>
                    <span v-else id="item-url-text">
                        slug:
                        {{ itemUrlParts[0] }}<SlugInput class="ml-1" :slug="itemUrlParts[1]" @onChange="onChange" />
                    </span>
                </blockquote>
            </div>
            <div v-else>
                Access to this {{ model_class }} is currently restricted so that only you and the users listed below can
                access it. Note that sharing a History will also allow access to all of its datasets.
            </div>
            <br />
            <h4>Share {{ model_class }} with Individual Users</h4>
            <div v-if="!isExposeEmail">
                <div v-if="item.users_shared_with && item.users_shared_with.length > 0">
                    <b-table small caption-top :fields="shareFields" :items="item.users_shared_with">
                        <template v-slot:table-caption>
                            The following users will see this {{ model_class }} in their {{ model_class }} list and will
                            be able to view, import and run it.
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
                    <p>You have not shared this {{ model_class }} with any users.</p>
                </div>
            </div>
            <SelectUsers
                v-else-if="item"
                :users_shared_with="item.users_shared_with"
                :share_with="actions.share_with"
                :unshare_with="actions.unshare_with"
                :plural-name="pluralNameLower"
                :id="id"
                :is-expose-email="isExposeEmail"
            />
            <b-button :href="shareUrl" id="share_with_a_user"> <span>Share with a user</span> </b-button>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink, faEdit } from "@fortawesome/free-solid-svg-icons";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import SlugInput from "components/Common/SlugInput";
import SelectUsers from "components/Sharing/SelectUsers/SelectUsers";
import axios from "axios";

Vue.use(BootstrapVue);

library.add(faLink);
library.add(faEdit);

export default {
    components: {
        FontAwesomeIcon,
        SlugInput,
        SelectUsers,
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
            isExposeEmail: Galaxy.config.expose_user_email || Galaxy.user.attributes.is_admin,
            ready: false,
            hasUsername: Galaxy.user.get("username"),
            newUsername: "",
            errMsg: null,
            item: {
                title: "title",
                username_and_slug: "username/slug",
                importable: false,
                published: false,
                users_shared_with: [],
            },
            shareFields: ["email", { key: "id", label: "" }],
            makeMembersPublic: false,
            showUrl: true,
            tooltipClipboard: "Copy URL",
            actions: {
                enable_link_access: "enable_link_access",
                disable_link_access: "disable_link_access",
                publish: "publish",
                unpublish: "unpublish",
                share_with: "share_with",
                unshare_with: "unshare_with",
            },
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
        itemRoot() {
            const port = window.location.port ? `:${window.location.port}` : "";
            return `${window.location.protocol}//${window.location.hostname}${port}${getAppRoot()}`;
        },
        itemUrl() {
            return `${this.itemRoot}${this.item.username_and_slug}`;
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
        showDanger() {
            return this.errMsg !== null;
        },
    },
    created: function () {
        this.getModel();
    },
    methods: {
        onCopy() {
            const clipboard = document.createElement("input");
            document.body.appendChild(clipboard);
            clipboard.value = this.itemUrl;
            clipboard.select();
            document.execCommand("copy");
            document.body.removeChild(clipboard);
            this.tooltipClipboard = "Copied!";
        },
        onCopyOut() {
            this.tooltipClipboard = "Copy URL";
        },
        onEdit() {
            this.showUrl = false;
        },
        onChange(newSlug) {
            this.showUrl = true;
            this.item.username_and_slug = `${this.itemSlugParts[0]}${newSlug}`;
            const requestUrl = `${this.slugUrl}&new_slug=${newSlug}`;
            axios.get(requestUrl).catch((error) => (this.errMsg = error.response.data.err_msg));
        },
        onImportable(importable) {
            if (importable) {
                this.setSharing(this.actions.enable_link_access);
            } else {
                this.item.published = false;
                this.setSharing(this.actions.disable_link_access);
            }
        },
        onPublish(published) {
            if (published) {
                this.item.importable = true;
                this.setSharing(this.actions.publish);
            } else {
                this.setSharing(this.actions.unpublish);
            }
        },
        getModel() {
            this.ready = false;
            axios
                .get(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`)
                .then((response) => {
                    this.item = response.data;
                    console.log(response.data);
                    this.ready = true;
                })
                .catch((error) => (this.errMsg = error.response.data.err_msg));
        },
        setUsername() {
            const Galaxy = getGalaxyInstance();
            axios
                .put(`${getAppRoot()}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.newUsername || "",
                })
                .then((response) => {
                    this.errMsg = null;
                    this.hasUsername = true;
                    this.getModel();
                })
                .catch((error) => (this.errMsg = error.response.data.err_msg));
        },
        setSharing(action, user_id) {
            const data = {
                action: action,
                user_id: user_id,
            };
            return axios
                .post(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`, data)
                .then((response) => {
                    if (response.data.skipped) {
                        this.errMsg = "Some of the items within this object were not published due to an error.";
                    }
                    this.item = response.data;
                    this.ready = true;
                })
                .catch((error) => (this.errMsg = error.response.data.err_msg));
        },
    },
};
</script>
