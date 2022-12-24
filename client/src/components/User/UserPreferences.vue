<template>
    <b-container fluid class="p-0">
        <h1 v-localize class="h-lg">User preferences</h1>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            <span v-localize>You are logged in as</span>
            <strong id="user-preferences-current-email">{{ email }}</strong>
            <span v-localize>and you are using</span>
            <strong>{{ diskUsage }}</strong>
            <span v-localize>of disk space.</span>
            <span v-localize>If this is more than expected, please visit the</span>
            <router-link id="edit-preferences-cloud-auth" to="/storage">
                <b v-localize>Storage Dashboard</b>
            </router-link>
            <span v-localize>to free up disk space.</span>
            <span v-if="enableQuotas">
                <span v-localize>Your disk quota is:</span>
                <strong>{{ diskQuota }}</strong
                >.
            </span>
        </p>
        <user-preferences-element v-for="(link, index) in activeLinks" :key="index" :icon="link.icon">
            <router-link :id="link.id" :to="`/user/${index}`">
                <b v-localize>{{ link.title }}</b>
            </router-link>
            <div class="form-text text-muted">
                {{ link.description }}
            </div>
        </user-preferences-element>
        <user-preferences-element icon="fa-key">
            <router-link id="edit-preferences-api-key" :to="`/user/api_key`">
                <b v-localize>Manage API Key</b>
            </router-link>
            <div v-localize class="form-text text-muted">Access your current API key or create a new one.</div>
        </user-preferences-element>
        <user-preferences-element icon="fa-cloud">
            <router-link id="edit-preferences-cloud-auth" :to="`/user/cloud_auth`">
                <b v-localize>Manage Cloud Authorization</b>
            </router-link>
            <div v-localize class="form-text text-muted">
                Add or modify the configuration that grants Galaxy to access your cloud-based resources.
            </div>
        </user-preferences-element>
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element v-if="!config.enable_oidc" icon="fa-id-card-o">
                <router-link id="manage-third-party-identities" :to="`/user/external_ids`">
                    <b v-localize>Manage Third-Party Identities</b>
                </router-link>
                <div v-localize class="form-text text-muted">
                    Connect or disconnect access to your third-party identities.
                </div>
            </user-preferences-element>
        </ConfigProvider>
        <user-preferences-element icon="fa-cubes">
            <router-link to="/custom_builds">
                <b v-localize>Manage Custom Builds</b>
            </router-link>
            <div v-localize class="form-text text-muted">Add or remove custom builds using history datasets.</div>
        </user-preferences-element>
        <user-preferences-element icon="fa-palette">
            <b-badge variant="danger">New!</b-badge>
            <a v-b-toggle.preference-themes-collapse href="#">
                <b v-localize>Pick a Color Theme</b>
            </a>
            <div v-localize class="form-text text-muted">Click here to change the user interface color theme.</div>
            <b-collapse id="preference-themes-collapse" class="mt-2">
                <ThemeSelector />
            </b-collapse>
        </user-preferences-element>
        <user-preferences-element icon="fa-plus-square-o">
            <a href="#" @click="toggleNotifications"><b v-localize>Enable notifications</b></a>
            <div v-localize class="form-text text-muted">
                Allow push and tab notifcations on job completion. To disable, revoke the site notification privilege in
                your browser.
            </div>
        </user-preferences-element>
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element v-if="!config.single_user" icon="fa-lock">
                <a id="edit-preferences-make-data-private" href="#" @click="makeDataPrivate">
                    <b v-localize>Make All Data Private</b>
                </a>
                <div v-localize class="form-text text-muted">Click here to make all data private.</div>
            </user-preferences-element>
        </ConfigProvider>
        <ConfigProvider v-slot="{ config }">
            <UserDeletion
                v-if="config && !config.single_user && config.enable_account_interface"
                :email="email"
                :user-id="userId">
            </UserDeletion>
        </ConfigProvider>
        <user-preferences-element v-if="hasLogout" icon="fa-sign-out">
            <a id="edit-preferences-sign-out" href="#" @click="signOut">
                <b v-localize>Sign Out</b>
            </a>
            <div v-localize class="form-text text-muted">Click here to sign out of all sessions.</div>
        </user-preferences-element>
    </b-container>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ThemeSelector from "./ThemeSelector.vue";
import { getGalaxyInstance } from "app";
import { safePath } from "utils/redirect";
import _l from "utils/localization";
import axios from "axios";
import QueryStringParsing from "utils/query-string-parsing";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import ConfigProvider from "components/providers/ConfigProvider";
import { userLogoutAll } from "utils/logout";
import UserDeletion from "./UserDeletion";
import UserPreferencesElement from "./UserPreferencesElement";

import "@fortawesome/fontawesome-svg-core";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
        UserDeletion,
        UserPreferencesElement,
        ThemeSelector,
    },
    props: {
        userId: {
            type: String,
            required: true,
        },
        enableQuotas: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            email: "",
            diskUsage: "",
            diskQuota: "",
            messageVariant: null,
            message: null,
            submittedNames: [],
        };
    },
    computed: {
        baseUrl() {
            return safePath("user");
        },
        activeLinks() {
            const activeLinks = {};
            const UserPreferencesModel = getUserPreferencesModel();
            for (const key in UserPreferencesModel) {
                if (!UserPreferencesModel[key].disabled) {
                    activeLinks[key] = UserPreferencesModel[key];
                }
            }
            return activeLinks;
        },
        hasLogout() {
            const Galaxy = getGalaxyInstance();
            return !!Galaxy.session_csrf_token && !config.single_user;
        },
    },
    created() {
        const message = QueryStringParsing.get("message");
        const status = QueryStringParsing.get("status");
        if (message && status) {
            this.message = message;
            this.messageVariant = status;
        }
        axios.get(safePath(`/api/users/${this.userId}`)).then((response) => {
            this.email = response.data.email;
            this.diskUsage = response.data.nice_total_disk_usage;
            this.diskQuota = response.data.quota;
        });
    },
    methods: {
        toggleNotifications() {
            if (window.Notification) {
                Notification.requestPermission().then(function (permission) {
                    //If the user accepts, let's create a notification
                    if (permission === "granted") {
                        new Notification("Notifications enabled", {
                            icon: "static/favicon.ico",
                        });
                    } else {
                        alert("Notifications disabled, please re-enable through browser settings.");
                    }
                });
            } else {
                alert("Notifications are not supported by this browser.");
            }
        },
        makeDataPrivate() {
            const Galaxy = getGalaxyInstance();
            if (
                confirm(
                    _l(
                        "WARNING: This will make all datasets (excluding library datasets) for which you have " +
                            "'management' permissions, in all of your histories " +
                            "private, and will set permissions such that all " +
                            "of your new data in these histories is created as private.  Any " +
                            "datasets within that are currently shared will need " +
                            "to be re-shared or published.  Are you sure you " +
                            "want to do this?"
                    )
                )
            ) {
                axios.post(safePath(`/history/make_private?all_histories=true`)).then((response) => {
                    Galaxy.modal.show({
                        title: _l("Datasets are now private"),
                        body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${safePath(
                            "/user/permissions"
                        )}">User Permissions</a> interface.`,
                        buttons: {
                            Close: () => {
                                Galaxy.modal.hide();
                            },
                        },
                    });
                });
            }
        },
        signOut() {
            const Galaxy = getGalaxyInstance();
            Galaxy.modal.show({
                title: _l("Sign out"),
                body: "Do you want to continue and sign out of all active sessions?",
                buttons: {
                    Cancel: function () {
                        Galaxy.modal.hide();
                    },
                    "Sign out": userLogoutAll,
                },
            });
        },
    },
};
</script>
<style scoped>
@import "user-styles.scss";
</style>
