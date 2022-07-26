<template>
    <div>
        <h3>
            Share or Publish {{ modelClass }} <span v-if="ready">`{{ item.title }}`</span>
        </h3>
        <div v-for="error in errors" :key="error">
            <b-alert show variant="danger" dismissible @dismissed="errors = errors.filter((e) => e !== error)">
                <ErrorMessage :message="error" :root="root()"> </ErrorMessage>
            </b-alert>
        </div>
        <br />
        <div v-if="!hasUsername">
            <div>To make a {{ modelClass }} accessible via link or publish it, you must create a public username:</div>
            <form class="form-group" @submit.prevent="setUsername()">
                <input v-model="newUsername" class="form-control" type="text" />
            </form>
            <b-button type="submit" variant="primary" @click="setUsername()">Set Username</b-button>
        </div>
        <div v-else-if="ready">
            <b-form-checkbox v-model="item.importable" switch class="make-accessible" @change="onImportable">
                Make {{ modelClass }} accessible
            </b-form-checkbox>
            <b-form-checkbox
                v-if="item.importable"
                v-model="item.published"
                class="make-publishable"
                switch
                @change="onPublish">
                Make {{ modelClass }} publicly available in
                <a :href="published_url" target="_top">Published {{ pluralName }}</a>
            </b-form-checkbox>
            <br />
            <div v-if="item.importable">
                <div>
                    This {{ modelClass }} is currently <strong>{{ itemStatus }}</strong
                    >.
                </div>
                <p>Anyone can view and import this {{ modelClass }} by visiting the following URL:</p>
                <blockquote>
                    <b-button v-b-tooltip.hover title="Edit URL" variant="link" size="sm" @click="onEdit">
                        <font-awesome-icon icon="edit" />
                    </b-button>
                    <b-button id="tooltip-clipboard" variant="link" size="sm" @click="onCopy" @mouseout="onCopyOut">
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
                Access to this {{ modelClass }} is currently restricted so that only you and the users listed below can
                access it. Note that sharing a History will also allow access to all of its datasets.
            </div>
            <br />
            <b-card no-body>
                <b-button
                    v-b-toggle.accordion-1
                    class="share-with-collapse"
                    variant="light"
                    @click="isCollapseVisible = !isCollapseVisible">
                    Share {{ modelClass }} with Individual Users
                    <font-awesome-icon :icon="isCollapseVisible ? `caret-up` : `caret-down`" />
                </b-button>
                <b-collapse id="accordion-1" accordion="main-accordion" role="tabpanel">
                    <ConfigProvider v-slot="{ config }">
                        <CurrentUser v-slot="{ user }">
                            <div v-if="user && config && !permissionsChangeRequired(item)">
                                <p v-if="item.users_shared_with.length === 0" class="share_with_title">
                                    You have not shared this {{ modelClass }} with any users.
                                </p>
                                <p v-else class="share_with_title">
                                    The following users will see this {{ modelClass }} in their {{ modelClass }} list
                                    and will be able to view, import and run it.
                                </p>

                                <b-alert
                                    :show="dismissCountDown"
                                    dismissible
                                    class="success-alert"
                                    variant="success"
                                    @dismissed="dismissCountDown = 0"
                                    @dismiss-count-down="dismissCountDown = $event">
                                    Sharing preferences are saved!
                                </b-alert>

                                <div class="share_with_view">
                                    <multiselect
                                        v-model="multiselectValues.sharingCandidates"
                                        :options="multiselectValues.userOptions"
                                        :clear-on-select="true"
                                        :multiple="true"
                                        :internal-search="false"
                                        :max-height="config.expose_user_email || user.is_admin ? 300 : 0"
                                        label="email"
                                        track-by="email"
                                        placeholder="Please specify user email"
                                        @close="onMultiselectBlur(config.expose_user_email || user.is_admin)"
                                        @search-change="
                                            searchChanged($event, config.expose_user_email || user.is_admin)
                                        ">
                                        <template v-if="!(config.expose_user_email || user.is_admin)" slot="caret">
                                            <div></div>
                                        </template>
                                        <template v-if="config.expose_user_email || user.is_admin" slot="noResult">
                                            <div v-if="threeCharactersEntered">
                                                {{ elementsNotFoundWarning }}
                                            </div>
                                            <div v-else>{{ charactersThresholdWarning }}</div>
                                        </template>
                                        <template slot="tag" slot-scope="{ option, remove }">
                                            <span
                                                class="multiselect__tag remove_sharing_with"
                                                :data-email="option.email">
                                                <span>{{ option.email }}</span>
                                                <i
                                                    aria-hidden="true"
                                                    tabindex="1"
                                                    class="multiselect__tag-icon"
                                                    @click="remove(option)"></i>
                                            </span>
                                        </template>
                                        <template slot="noOptions">
                                            <div v-if="threeCharactersEntered">
                                                {{ charactersThresholdWarning }}
                                            </div>
                                            <div v-else>
                                                {{ elementsNotFoundWarning }}
                                            </div>
                                        </template>
                                    </multiselect>
                                    <div class="share-with-card-buttons">
                                        <!--submit/cancel buttons-->
                                        <b-button
                                            variant="outline-danger"
                                            class="sharing_icon cancel-sharing-with"
                                            @click="getSharing()">
                                            Cancel
                                        </b-button>
                                        <b-button
                                            v-b-tooltip.hover.bottom
                                            variant="outline-primary"
                                            :disabled="
                                                !(sharedWithUsersChanged || !!multiselectValues.currentUserSearch)
                                            "
                                            :title="submitBtnTitle"
                                            class="sharing_icon submit-sharing-with"
                                            @click.stop="
                                                setSharing(
                                                    actions.share_with,
                                                    multiselectValues.sharingCandidates.map(({ email }) => email)
                                                )
                                            ">
                                            {{ multiselectValues.currentUserSearch ? `Add` : `Save` }}
                                        </b-button>
                                    </div>
                                </div>
                            </div>
                        </CurrentUser>
                    </ConfigProvider>
                    <b-alert variant="warning" dismissible fade :show="permissionsChangeRequired(item)">
                        <div class="text-center">
                            {{
                                item.extra.can_change.length > 0
                                    ? `${item.extra.can_change.length} datasets are exclusively private to you`
                                    : `You are not authorized to share ${item.extra.cannot_change.length} datasets`
                            }}
                        </div>
                    </b-alert>
                    <b-row v-if="permissionsChangeRequired(item)">
                        <b-col v-if="item.extra.can_change.length > 0">
                            <b-card>
                                <b-card-header header-tag="header" class="p-1" role="tab">
                                    <b-button v-b-toggle.can-share block variant="warning">
                                        Datasets can be shared by updating their permissions
                                    </b-button>
                                </b-card-header>
                                <b-collapse id="can-share" visible accordion="can-share-accordion" role="tabpanel">
                                    <b-list-group>
                                        <b-list-group-item v-for="dataset in item.extra.can_change" :key="dataset.id">{{
                                            dataset.name
                                        }}</b-list-group-item>
                                    </b-list-group>
                                </b-collapse>
                            </b-card>
                        </b-col>
                        <b-col v-if="item.extra.cannot_change.length > 0">
                            <b-card>
                                <b-card-header header-tag="header" class="p-1" role="tab">
                                    <b-button v-b-toggle.cannot-share block variant="danger"
                                        >Datasets cannot be shared, you are not authorized to change
                                        permissions</b-button
                                    >
                                </b-card-header>
                                <b-collapse id="cannot-share" visible accordion="cannot-accordion2" role="tabpanel">
                                    <b-list-group>
                                        <b-list-group-item
                                            v-for="dataset in item.extra.cannot_change"
                                            :key="dataset.id"
                                            >{{ dataset.name }}</b-list-group-item
                                        >
                                    </b-list-group>
                                </b-collapse>
                            </b-card>
                        </b-col>
                        <b-col>
                            <b-card
                                border-variant="primary"
                                header="How would you like to proceed?"
                                header-bg-variant="primary"
                                header-text-variant="white"
                                align="center">
                                <b-button
                                    v-if="item.extra.can_change.length > 0"
                                    block
                                    variant="outline-primary"
                                    @click="
                                        setSharing(
                                            actions.share_with,
                                            multiselectValues.sharingCandidates.map(({ email }) => email),
                                            share_option.make_public
                                        )
                                    "
                                    >Make datasets public</b-button
                                >
                                <b-button
                                    v-if="item.extra.can_change.length > 0"
                                    block
                                    variant="outline-primary"
                                    @click="
                                        setSharing(
                                            actions.share_with,
                                            multiselectValues.sharingCandidates.map(({ email }) => email),
                                            share_option.make_accessible_to_shared
                                        )
                                    "
                                    >Make datasets private to me and
                                    {{ multiselectValues.sharingCandidates.map(({ email }) => email).join() }}</b-button
                                >
                                <b-button
                                    block
                                    variant="outline-primary"
                                    @click="
                                        setSharing(
                                            actions.share_with,
                                            multiselectValues.sharingCandidates.map(({ email }) => email),
                                            share_option.no_changes
                                        )
                                    ">
                                    Share Anyway
                                </b-button>
                                <b-button block variant="outline-danger" @click="getSharing()">Cancel </b-button>
                            </b-card>
                        </b-col>
                    </b-row>
                </b-collapse>
            </b-card>
        </div>
    </div>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCopy, faEdit, faUserPlus, faUserSlash, faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { getAppRoot } from "onload/loadConfig";
import { getGalaxyInstance } from "app";
import SlugInput from "components/Common/SlugInput";
import axios from "axios";
import Multiselect from "vue-multiselect";
import { copy } from "utils/clipboard";
import ConfigProvider from "components/providers/ConfigProvider";
import CurrentUser from "components/providers/CurrentUser";
import { errorMessageAsString } from "utils/simple-error";
import ErrorMessage from "./ErrorMessage";

Vue.use(BootstrapVue);
library.add(faCopy, faEdit, faUserPlus, faUserSlash, faCaretDown, faCaretUp);
const defaultExtra = () => {
    return {
        cannot_change: [],
        can_change: [],
        can_share: true,
    };
};
export default {
    components: {
        ConfigProvider,
        ErrorMessage,
        FontAwesomeIcon,
        SlugInput,
        Multiselect,
        CurrentUser,
    },
    props: {
        id: {
            type: String,
            required: true,
        },
        pluralName: {
            type: String,
            required: true,
        },
        modelClass: {
            type: String,
            required: true,
        },
    },
    data() {
        const Galaxy = getGalaxyInstance();
        return {
            isCollapseVisible: false,
            dismissCountDown: 0,
            charactersThresholdWarning: "Enter at least 3 characters to see suggestions",
            elementsNotFoundWarning: "No elements found. Consider changing the search query.",
            ready: false,
            threeCharactersEntered: true,
            hasUsername: Galaxy.user.get("username"),
            newUsername: "",
            errors: [],
            multiselectValues: {
                sharingCandidates: [],
                userOptions: [],
                currentUserSearch: "",
            },
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
            actions: {
                enable_link_access: "enable_link_access",
                disable_link_access: "disable_link_access",
                publish: "publish",
                unpublish: "unpublish",
                share_with: "share_with_users",
            },
            share_option: {
                make_public: "make_public",
                make_accessible_to_shared: "make_accessible_to_shared",
                no_changes: "no_changes",
            },
        };
    },
    computed: {
        sharedWithUsersChanged() {
            if (this.item.users_shared_with.length !== this.multiselectValues.sharingCandidates.length) {
                return true;
            }

            return !this.multiselectValues.sharingCandidates.every(({ email }) =>
                this.item.users_shared_with.some((user) => user.email === email)
            );
        },
        submitBtnTitle() {
            if (this.multiselectValues.currentUserSearch) {
                return "";
            } else {
                return this.multiselectValues.sharingCandidates && this.multiselectValues.sharingCandidates.length > 0
                    ? `Share with ${this.multiselectValues.sharingCandidates.map(({ email }) => email)}`
                    : "Please enter user email";
            }
        },

        pluralNameLower() {
            return this.pluralName.toLowerCase();
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
        this.getSharing();
    },
    methods: {
        root() {
            return getAppRoot();
        },
        permissionsChangeRequired(item) {
            if (!item.extra) {
                return false;
            }
            return item.extra && (item.extra.can_change.length > 0 || item.extra.cannot_change.length > 0);
        },
        onMultiselectBlur(isAdmin) {
            const isValueChosen = this.multiselectValues.sharingCandidates.some(
                (item) => item.email === this.multiselectValues.currentUserSearch
            );
            if (this.multiselectValues.currentUserSearch && !isValueChosen && !isAdmin) {
                this.multiselectValues.sharingCandidates.push({ email: this.multiselectValues.currentUserSearch });
            }
        },
        onError(axiosError) {
            this.addError(errorMessageAsString(axiosError));
        },
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
        assignItem(newItem, overwriteCandidates) {
            if (newItem.errors) {
                this.errors = newItem.errors;
            }
            this.item = newItem;
            if (overwriteCandidates) {
                this.multiselectValues.sharingCandidates = Array.from(newItem.users_shared_with);
            }
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
                .then(() => (this.item.username_and_slug = `${this.itemSlugParts[0]}${newSlug}`))
                .catch(this.onError);
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
        getSharing() {
            this.ready = false;
            this.dismissCountDown = 0;
            axios
                .get(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/sharing`)
                .then((response) => this.assignItem(response.data, true))
                .catch(this.onError);
        },
        setUsername() {
            const Galaxy = getGalaxyInstance();
            axios
                .put(`${getAppRoot()}api/users/${Galaxy.user.id}/information/inputs`, {
                    username: this.newUsername || "",
                })
                .then((response) => {
                    this.hasUsername = true;
                    this.getSharing();
                })
                .catch(this.onError);
        },
        setSharing(action, user_id, share_option) {
            let user_ids = undefined;
            if (Array.isArray(user_id)) {
                user_ids = user_id;
            } else {
                user_ids = user_id ? user_id.replace(/ /g, "").split(",") : undefined;
            }

            const data = {
                user_ids: user_ids,
                share_option: share_option ? share_option : undefined,
            };
            return axios
                .put(`${getAppRoot()}api/${this.pluralNameLower}/${this.id}/${action}`, data)
                .then(({ data }) => {
                    this.errors = [];
                    const userIdsSaved = user_ids && !this.permissionsChangeRequired(data) && data.errors.length === 0;
                    this.assignItem(data, userIdsSaved);

                    if (userIdsSaved) {
                        this.dismissCountDown = 3;
                    }
                })
                .catch(this.onError);
        },
        searchChanged(searchValue, exposedUsers) {
            this.multiselectValues.currentUserSearch = searchValue;
            if (!exposedUsers) {
                this.multiselectValues.userOptions = [{ email: searchValue }];
            } else if (searchValue.length < 3) {
                this.threeCharactersEntered = false;
                this.multiselectValues.userOptions = [];
            } else {
                this.threeCharactersEntered = true;
                axios
                    .get(`${getAppRoot()}api/users?f_email=${searchValue}`)
                    .then((response) => {
                        this.multiselectValues.userOptions = response.data.filter(
                            ({ email }) =>
                                !this.multiselectValues.sharingCandidates.map(({ email }) => email).includes(email)
                        );
                    })
                    .catch(this.onError);
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
    margin: 1rem 1rem;
}
.share_with_title {
    text-align: center;
    padding-top: 1.1rem;
}

.success-alert {
    margin: 0.3rem 2rem 0.9rem;
}
.share-with-card-buttons {
    margin: 0.5rem 0;
    float: right;
}
</style>
