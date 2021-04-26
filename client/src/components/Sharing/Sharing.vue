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
            <p>
                The following users will see this {{ model_class }} in their {{ model_class }} list and will be able to
                view, import and run it.
            </p>
            <div v-if="!isExposeEmail">
                <b-table
                    class="share_with_table"
                    show-empty
                    foot-clone
                    small
                    caption-top
                    :fields="shareFields"
                    :items="item.users_shared_with"
                >
                    <template #empty="scope">
                        <p>You have not shared this {{ model_class }} with any users.</p>
                    </template>

                    <template v-slot:cell(id)="cell">
                        <b-button
                            variant="danger"
                            size="sm"
                            @click="setSharing(actions.share_with, shareWithEmail)"
                            class="sharing_icon"
                        >
                            <font-awesome-icon
                                class="unshare_user sharing_icon"
                                @click.stop="setSharing(actions.unshare_with, cell.value)"
                                icon="user-slash"
                            />
                        </b-button>
                    </template>
                    <template #foot(email)="cell">
                        <b-form-input v-model="shareWithEmail" placeholder="Please enter user email" />
                    </template>
                    <template #foot(id)="cell">
                        <b-button
                            variant="link"
                            size="sm"
                            @click.stop="setSharing(actions.share_with, shareWithEmail)"
                            v-b-tooltip.hover
                            :title="shareWithEmail ? `Share with ${shareWithEmail}` : ''"
                            class="sharing_icon"
                        >
                            <font-awesome-icon class="share_with" icon="user-plus" size="lg" />
                        </b-button>
                    </template>
                </b-table>
            </div>
            <SelectUsers
                v-else-if="item"
                :users_shared_with="item.users_shared_with"
                :share_with="actions.share_with"
                :unshare_with="actions.unshare_with"
                :plural-name="pluralNameLower"
                :id="id"
                :is-expose-email="isExposeEmail"
                @shared_with="shared_with"
            />
            <b-alert show v-if="share_with_err" variant="danger" dismissible> {{ share_with_err }} </b-alert>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLink, faEdit, faUserPlus, faUserSlash } from "@fortawesome/free-solid-svg-icons";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import SlugInput from "components/Common/SlugInput";
import SelectUsers from "components/Sharing/SelectUsers/SelectUsers";
import axios from "axios";

Vue.use(BootstrapVue);
[faLink, faEdit, faUserPlus, faUserSlash].forEach((icon) => library.add(icon));

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
            share_with_err: undefined,
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
            shareWithEmail: "",
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
        slugUrl() {
            return `${getAppRoot()}api/${this.pluralNameLower}/${this.id}/slug`;
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

            const requestUrl = `${this.slugUrl}/${newSlug}`;
            axios
                .put(requestUrl, {
                    new_slug: newSlug,
                })
                .then((response) => {
                    this.errMsg = null;
                    this.item.username_and_slug = `${this.itemSlugParts[0]}${newSlug}`;
                })
                .catch((error) => (this.errMsg = error.response.data.err_msg));
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
            if (
                action === this.actions.share_with &&
                this.item.users_shared_with.some((user) => user_id === user.email)
            ) {
                this.share_with_err = `You already shared this ${this.model_class} with ${user_id}`;
                return;
            }

            const data = {
                action: action,
                user_ids: user_id ? [user_id] : undefined,
            };
            return axios
                .post(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`, data)
                .then((response) => {
                    if (response.data.skipped) {
                        this.errMsg = "Some of the items within this object were not published due to an error.";
                    }
                    this.share_with_err = response.data.share_with_err;
                    this.item = response.data;
                    this.ready = true;
                    this.shareWithEmail = "";
                })
                .catch((error) => (this.errMsg = error.response.data.err_msg));
        },
        shared_with(user) {
            this.item.users_shared_with.push(user);
        },
    },
};
</script>

<style scoped>
.sharing_icon {
    margin-top: 0.15rem;
}
.share_with_table {
    max-width: 680px;
}
</style>
