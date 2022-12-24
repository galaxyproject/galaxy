<template>
    <b-container fluid class="p-0">
        <h1 v-localize class="h-lg">User preferences</h1>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            <span v-localize>You are logged in as</span>
            <strong id="user-preferences-current-email">{{ email }}</strong
            >.
        </p>
        <b-row v-for="(link, index) in activeLinks" :key="index" class="ml-3 mb-1">
            <i :class="['pref-icon pt-1 fa fa-lg', link.icon]" />
            <div class="pref-content pr-1">
                <a v-if="link.onclick" :id="link.id" href="javascript:void(0)" @click="link.onclick">
                    <b>{{ link.title }}</b>
                </a>
                <a v-else :id="link.id" :href="`${baseUrl}/${index}`">
                    <b>{{ link.title }}</b>
                </a>
                <div class="form-text text-muted">
                    {{ link.description }}
                </div>
            </div>
        </b-row>
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element v-if="!config.enable_oidc" icon="fa-id-card-o">
                <a id="manage-third-party-identities" :href="`${baseUrl}/external_ids`">
                    <b v-localize>Manage Third-Party Identities</b>
                </a>
                <div v-localize class="form-text text-muted">
                    Connect or disconnect access to your third-party identities.
                </div>
            </user-preferences-element>
        </ConfigProvider>
        <user-preferences-element icon="fa-cloud">
            <a id="edit-preferences-cloud-auth" :href="`${baseUrl}/cloud_auth`">
                <b v-localize>Manage Cloud Authorization</b>
            </a>
            <div v-localize class="form-text text-muted">
                Add or modify the configuration that grants Galaxy to access your cloud-based resources.
            </div>
        </user-preferences-element>
        <user-preferences-element icon="fa-key">
            <a id="edit-preferences-api-key" :href="`${baseUrl}/api_key`">
                <b v-localize>Manage API Key</b>
            </a>
            <div v-localize class="form-text text-muted">Access your current API key or create a new one.</div>
        </user-preferences-element>
        <user-preferences-element icon="fa-cubes">
            <a href="javascript:void(0)" @click="openManageCustomBuilds">
                <b v-localize>Manage Custom Builds</b>
            </a>
            <div v-localize class="form-text text-muted">Add or remove custom builds using history datasets.</div>
        </user-preferences-element>
        <user-preferences-element icon="fa-palette">
            <b-badge variant="danger">New!</b-badge>
            <a v-b-toggle.preference-themes-collapse href="javascript:void(0)">
                <b v-localize>Pick a Color Theme</b>
            </a>
            <div v-localize class="form-text text-muted">Click here to change the user interface color theme.</div>
            <b-collapse id="preference-themes-collapse" class="mt-2">
                <ThemeSelector />
            </b-collapse>
        </user-preferences-element>
        <user-preferences-element icon="fa-plus-square-o">
            <a href="javascript:void(0)" @click="toggleNotifications"><b v-localize>Enable notifications</b></a>
            <div v-localize class="form-text text-muted">
                Allow push and tab notifcations on job completion. To disable, revoke the site notification privilege in
                your browser.
            </div>
        </user-preferences-element>
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element v-if="!config.single_user" icon="fa-lock">
                <a id="edit-preferences-make-data-private" href="javascript:void(0)" @click="makeDataPrivate">
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
            <a id="edit-preferences-sign-out" href="javascript:void(0)" @click="signOut"><b v-localize>Sign Out</b></a>
            <div v-localize class="form-text text-muted">Click here to sign out of all sessions.</div>
        </user-preferences-element>
        <p class="mt-2">
            You are using <strong>{{ diskUsage }}</strong> of disk space in this Galaxy instance.
            <span v-if="enableQuotas">
                Your disk quota is: <strong>{{ diskQuota }}</strong
                >.
            </span>
            Is your usage more than expected? Review your
            <b-link :href="storageDashboardUrl"><b>Storage Dashboard</b></b-link
            >.
        </p>
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
            storageDashboardUrl: safePath("/storage"),
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
        openManageCustomBuilds() {
            this.$router.push(`/custom_builds`);
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
