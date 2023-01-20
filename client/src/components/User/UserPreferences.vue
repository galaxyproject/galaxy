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
        <user-preferences-element
            v-for="(link, index) in activePreferences"
            :id="link.id"
            :key="index"
            :icon="link.icon"
            :title="link.title"
            :description="link.description"
            :to="`/user/${index}`" />
        <user-preferences-element
            id="edit-preferences-api-key"
            icon="fa-key"
            title="Manage API Key"
            description="Access your current API key or create a new one."
            to="/user/api_key" />
        <user-preferences-element
            id="edit-preferences-cloud-auth"
            icon="fa-cloud"
            title="Manage Cloud Authorization"
            description="Add or modify the configuration that grants Galaxy to access your cloud-based resources."
            to="/user/cloud_auth" />
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element
                v-if="!config.enable_oidc"
                id="manage-third-party-identities"
                icon="fa-id-card-o"
                title="Manage Third-Party Identities"
                description="Connect or disconnect access to your third-party identities."
                to="/user/external_ids" />
        </ConfigProvider>
        <user-preferences-element
            id="edit-preferences-custom-builds"
            icon="fa-cubes"
            title="Manage Custom Builds"
            description="Add or remove custom builds using history datasets."
            to="/custom_builds" />
        <user-preferences-element
            v-if="hasThemes"
            icon="fa-palette"
            title="Pick a Color Theme"
            description="Click here to change the user interface color theme."
            badge="New!"
            @click="toggleTheme = !toggleTheme">
            <b-collapse v-model="toggleTheme">
                <ThemeSelector />
            </b-collapse>
        </user-preferences-element>
        <user-preferences-element
            id="edit-preferences-notifications"
            icon="fa-plus-square-o"
            title="Enable notifications"
            description="Allow push and tab notifcations on job completion. To disable, revoke the site notification privilege in your browser."
            @click="toggleNotifications" />
        <ConfigProvider v-slot="{ config }">
            <user-preferences-element
                v-if="!config.single_user"
                id="edit-preferences-make-data-private"
                icon="fa-lock"
                title="Make All Data Private"
                description="Click here to make all data private."
                @click="makeDataPrivate" />
        </ConfigProvider>
        <ConfigProvider v-slot="{ config }">
            <UserBeaconSettings v-if="config && config.enable_beacon_integration" :user-id="userId"
                >>
            </UserBeaconSettings>
        </ConfigProvider>
        <ConfigProvider v-slot="{ config }">
            <UserDeletion
                v-if="config && !config.single_user && config.enable_account_interface"
                :email="email"
                :user-id="userId">
            </UserDeletion>
        </ConfigProvider>
        <user-preferences-element
            v-if="hasLogout"
            id="edit-preferences-sign-out"
            icon="fa-sign-out"
            title="Sign Out"
            description="Click here to sign out of all sessions."
            @click="signOut" />
    </b-container>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import ThemeSelector from "./ThemeSelector.vue";
import { getGalaxyInstance } from "app";
import { withPrefix } from "utils/redirect";
import _l from "utils/localization";
import axios from "axios";
import QueryStringParsing from "utils/query-string-parsing";
import { getUserPreferencesModel } from "components/User/UserPreferencesModel";
import ConfigProvider from "components/providers/ConfigProvider";
import { userLogoutAll } from "utils/logout";
import UserDeletion from "./UserDeletion";
import UserPreferencesElement from "./UserPreferencesElement";

import "@fortawesome/fontawesome-svg-core";
import UserBeaconSettings from "./UserBeaconSettings";

Vue.use(BootstrapVue);

export default {
    components: {
        ConfigProvider,
        UserDeletion,
        UserPreferencesElement,
        ThemeSelector,
        UserBeaconSettings,
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
            toggleTheme: false,
        };
    },
    computed: {
        activePreferences() {
            const enabledPreferences = Object.entries(getUserPreferencesModel()).filter((f) => !f.disabled);
            return Object.fromEntries(enabledPreferences);
        },
        hasLogout() {
            const Galaxy = getGalaxyInstance();
            return !!Galaxy.session_csrf_token && !Galaxy.config.single_user;
        },
        hasThemes() {
            const Galaxy = getGalaxyInstance();
            const themes = Object.keys(Galaxy.config.themes);
            return themes?.length > 1 ?? false;
        },
    },
    created() {
        const message = QueryStringParsing.get("message");
        const status = QueryStringParsing.get("status");
        if (message && status) {
            this.message = message;
            this.messageVariant = status;
        }
        axios.get(withPrefix(`/api/users/${this.userId}`)).then((response) => {
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
                axios.post(withPrefix(`/history/make_private?all_histories=true`)).then((response) => {
                    Galaxy.modal.show({
                        title: _l("Datasets are now private"),
                        body: `All of your histories and datsets have been made private.  If you'd like to make all *future* histories private please use the <a href="${withPrefix(
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
