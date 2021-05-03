<template>
    <div v-if="ready">
        <h3>Share or Publish {{ model_class }} `{{ item.title }}`</h3>
        <div v-for="error in errors" :key="error">
            <b-alert show variant="danger" dismissible @dismissed="errors = errors.filter((e) => e !== error)">
                {{ error }}
            </b-alert>
        </div>
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
                        <font-awesome-icon :icon="['far', 'copy']" />
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
                    class="share_with_view"
                    show-empty
                    :foot-clone="!permissionsChangeRequired"
                    small
                    caption-top
                    :fields="shareFields"
                    :items="item.users_shared_with"
                >
                    <template v-slot:empty>
                        <p>You have not shared this {{ model_class }} with any users.</p>
                    </template>

                    <template v-slot:cell(id)="cell">
                        <b-button
                            variant="outline-danger"
                            size="sm"
                            class="sharing_icon"
                            @click.stop="setSharing(actions.unshare_with, cell.value)"
                        >
                            <font-awesome-icon class="unshare_user sharing_icon" size="lg" icon="user-slash" />
                        </b-button>
                    </template>
                    <template v-slot:foot(email)>
                        <b-form-input
                            v-model="shareWithEmail"
                            class="user-email-input-form"
                            placeholder="Please enter user email(s) using comma separated values"
                        />
                    </template>
                    <template v-slot:foot(id)>
                        <b-button
                            variant="outline-primary"
                            size="sm"
                            :disabled="shareWithEmail === ''"
                            @click.stop="setSharing(actions.share_with, shareWithEmail)"
                            v-b-tooltip.hover.bottom
                            :title="shareWithEmail ? `Share with ${shareWithEmail}` : 'Please enter user email'"
                            class="sharing_icon submit-sharing-with"
                        >
                            <font-awesome-icon class="share_with" icon="user-plus" size="lg" />
                        </b-button>
                    </template>
                </b-table>
            </div>
            <multiselect
                v-else-if="item && !permissionsChangeRequired"
                class="select-users"
                v-model="item.users_shared_with"
                :options="usersList"
                :clear-on-select="true"
                :preserve-search="true"
                :multiple="true"
                @select="setSharing(actions.share_with, $event.email)"
                @remove="setSharing(actions.unshare_with, $event.email)"
                label="email"
                track-by="id"
                @search-change="searchChanged"
                :internal-search="false"
            >
                <template slot="noOptions">
                    <div>
                        {{ emptyResult }}
                    </div>
                </template>
            </multiselect>

            <!--            <b-card-group header-tag="header" no-body role="tab"  deck>-->
            <b-alert variant="warning" dismissible fade :show="permissionsChangeRequired">
                <div class="text-center">
                    {{
                        item.extra.can_change.length > 0
                            ? `${item.extra.can_change.length} datasets are exclusively private to you`
                            : `You are not authorized to share ${item.extra.cannot_change.length} datasets`
                    }}
                </div>
            </b-alert>
            <b-row v-if="permissionsChangeRequired">
                <b-col v-if="item.extra.can_change.length > 0">
                    <b-card>
                        <b-card-header header-tag="header" class="p-1" role="tab">
                            <b-button block v-b-toggle.can-share variant="warning"
                                >Datasets can be shared by updating their permissions</b-button
                            >
                        </b-card-header>
                        <b-collapse id="can-share" visible accordion="my-accordion" role="tabpanel">
                            <b-list-group>
                                <b-list-group-item :key="dataset.id" v-for="dataset in item.extra.can_change">{{
                                    dataset.name
                                }}</b-list-group-item>
                            </b-list-group>
                        </b-collapse>
                    </b-card>
                </b-col>
                <b-col v-if="item.extra.cannot_change.length > 0">
                    <b-card>
                        <b-card-header header-tag="header" class="p-1" role="tab">
                            <b-button block v-b-toggle.cannot-share variant="danger"
                                >Datasets cannot be shared, you are not authorized to change permissions</b-button
                            >
                        </b-card-header>
                        <b-collapse id="cannot-share" visible accordion="my-accordion2" role="tabpanel">
                            <b-list-group>
                                <b-list-group-item :key="dataset.id" v-for="dataset in item.extra.cannot_change">{{
                                    dataset.name
                                }}</b-list-group-item>
                            </b-list-group>
                        </b-collapse>
                    </b-card>
                </b-col>
                <b-col>
                    <b-card
                        border-variant="primary"
                        header="How would like to proceed?"
                        header-bg-variant="primary"
                        header-text-variant="white"
                        align="center"
                    >
                        <b-button
                            @click="setSharing(actions.share_with, shareWithEmail, share_option.make_public)"
                            v-if="item.extra.can_change.length > 0"
                            block
                            variant="outline-primary"
                            >Make datasets public</b-button
                        >
                        <b-button
                            @click="
                                setSharing(actions.share_with, shareWithEmail, share_option.make_accessible_to_shared)
                            "
                            v-if="item.extra.can_change.length > 0"
                            block
                            variant="outline-primary"
                            >Share only with {{ shareWithEmail }}</b-button
                        >
                        <b-button
                            @click="setSharing(actions.share_with, shareWithEmail, share_option.no_changes)"
                            block
                            variant="outline-primary"
                            >Share Anyway
                        </b-button>
                        <b-button @click="getModel()" block variant="outline-danger">Cancel </b-button>
                    </b-card>
                </b-col>
            </b-row>
            <!--            </b-card-group>-->
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faEdit, faUserPlus, faUserSlash } from "@fortawesome/free-solid-svg-icons";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import SlugInput from "components/Common/SlugInput";
import axios from "axios";
import Multiselect from "vue-multiselect";
import { copy } from "utils/clipboard";

Vue.use(BootstrapVue);
[faCopy, faEdit, faUserPlus, faUserSlash].forEach((icon) => library.add(icon));

const defaultExtra = () => {
    return {
        cannot_change: [],
        can_change: [],
        can_share: true,
    };
};
export default {
    components: {
        FontAwesomeIcon,
        SlugInput,
        Multiselect,
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
            usersList: [],
            emptyResult: "Please enter user email",
            ready: false,
            hasUsername: Galaxy.user.get("username"),
            newUsername: "",
            errors: [],
            item: {
                title: "title",
                username_and_slug: "username/slug",
                importable: false,
                published: false,
                users_shared_with: [],
                extra: defaultExtra(),
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
            share_option: {
                make_public: "make_public",
                make_accessible_to_shared: "make_accessible_to_shared",
                no_changes: "no_changes",
            },
        };
    },
    computed: {
        permissionsChangeRequired() {
            if (!this.item.extra) return false;
            return (
                this.item.extra && (this.item.extra.can_change.length > 0 || this.item.extra.cannot_change.length > 0)
            );
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
    },
    created: function () {
        this.getModel();
    },
    methods: {
        addError(newError) {
            // temporary turning Set into Array, until we update till Vue 3.0, that supports Set reactivity
            this.errors = Array.from(new Set(this.errors).add(newError));
        },
        onCopy() {
            copy(this.itemUrl);
            this.tooltipClipboard = "Copied!";
        },
        onCopyOut() {
            this.tooltipClipboard = "Copy URL";
        },
        onEdit() {
            this.showUrl = false;
        },
        assignItem(newItem) {
            if (newItem.errors) this.errors = newItem.errors;
            this.item = newItem;
            if (!this.item.extra || newItem.errors.length > 0) {
                this.item.extra = defaultExtra();
            }

            this.ready = true;
        },
        onChange(newSlug) {
            this.showUrl = true;
            const requestUrl = `${this.slugUrl}`;
            axios
                .put(requestUrl, {
                    new_slug: newSlug,
                })
                .then((response) => {
                    this.errMsg = null;
                    this.assignItem(response.data);
                    this.item.username_and_slug = `${this.itemSlugParts[0]}${newSlug}`;
                })
                .catch((error) => this.addError(error.response.data.err_msg));
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
                .then((response) => this.assignItem(response.data))
                .catch((error) => this.addError(error.response.data.err_msg));
        },
        setUsername() {
            const Galaxy = getGalaxyInstance();
            axios
                .put(`${getAppRoot()}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.newUsername || "",
                })
                .then((response) => {
                    this.hasUsername = true;
                    this.getModel();
                })
                .catch((error) => this.addError(error.response.data.err_msg));
        },
        setSharing(action, user_id, share_option) {
            let user_ids = undefined;
            if (user_id) {
                if (user_id.includes(",")) {
                    user_ids = user_id.replace(/ /g, "").split(",");
                } else user_ids = [user_id];
            }

            if (
                action === this.actions.share_with &&
                user_ids &&
                this.item.users_shared_with.some(({ email }) => user_ids.includes(email))
            ) {
                this.addError(
                    `You already shared this ${this.model_class} with
                    ${user_ids.filter((user) => this.item.users_shared_with.some(({ email }) => email === user))}`
                );
                return;
            }

            const data = {
                user_ids: user_ids,
                share_option: share_option ? share_option : undefined,
            };
            return axios
                .put(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/${action}`, data)
                .then(({ data }) => {
                    this.errors = [];
                    this.assignItem(data);
                    if (data.extra && data.extra.can_share) this.shareWithEmail = "";
                    else this.shareWithEmail = user_id || "";
                })
                .catch((error) => this.addError(error.response.data.err_msg));
        },
        searchChanged(searchValue) {
            if (searchValue === "") {
                this.usersList = [];
            } else {
                axios
                    .get(`${getAppRoot()}api/users?f_email=${searchValue}`)
                    .then((response) => {
                        this.usersList = response.data;
                    })
                    .catch((error) => this.addError(error.response.data.err_msg));
            }
        },
    },
};
</script>

<style scoped>
.sharing_icon {
    margin-top: 0.15rem;
}
.share_with_view {
    max-width: 680px;
}
</style>
