<template>
    <b-container fluid class="p-0">
        <h1 v-localize class="h-lg">User preferences</h1>
        <b-alert :variant="messageVariant" :show="!!message">
            {{ message }}
        </b-alert>
        <p>
            <span v-localize>You are signed in as</span>
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
        <UserPreferencesElement
            v-for="(link, index) in activePreferences"
            :id="link.id"
            :key="index"
            :icon="link.icon"
            :title="link.title"
            :description="link.description"
            :to="`/user/${index}`" />
        <UserPreferencesElement
            v-if="isConfigLoaded && !config.single_user"
            id="edit-preferences-permissions"
            :icon="faUsers"
            title="Set Dataset Permissions for New Histories"
            description="Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored."
            to="/user/permissions" />
        <UserPreferencesElement
            id="edit-preferences-api-key"
            :icon="faKey"
            title="Manage API Key"
            description="Access your current API key or create a new one."
            to="/user/api_key" />
        <UserPreferencesElement
            id="edit-preferences-notifications"
            :icon="faBell"
            title="Manage Notifications"
            description="Manage your notification settings."
            to="/user/notifications/preferences" />
        <UserPreferencesElement
            id="edit-preferences-cloud-auth"
            :icon="faCloud"
            title="Manage Cloud Authorization"
            description="Add or modify the configuration that grants Galaxy to access your cloud-based resources."
            to="/user/cloud_auth" />
        <UserPreferencesElement
            v-if="isConfigLoaded && config.enable_oidc && !config.fixed_delegated_auth"
            id="manage-third-party-identities"
            :icon="faIdCardAlt"
            title="Manage Third-Party Identities"
            description="Connect or disconnect access to your third-party identities."
            to="/user/external_ids" />
        <UserPreferencesElement
            id="edit-preferences-custom-builds"
            :icon="faCubes"
            title="Manage Custom Builds"
            description="Add or remove custom builds using history datasets."
            to="/custom_builds" />
        <UserPreferencesElement
            v-if="hasThemes"
            :icon="faPalette"
            title="Pick a Color Theme"
            description="Click here to change the user interface color theme."
            badge="New!"
            @click="toggleTheme = !toggleTheme">
            <b-collapse v-model="toggleTheme">
                <ThemeSelector />
            </b-collapse>
        </UserPreferencesElement>
        <UserPreferencesElement
            v-if="isConfigLoaded && !config.single_user"
            id="edit-preferences-make-data-private"
            :icon="faLock"
            title="Make All Data Private"
            description="Click here to make all data private."
            @click="makeDataPrivate" />
        <UserBeaconSettings v-if="isConfigLoaded && config.enable_beacon_integration" :user-id="userId">
        </UserBeaconSettings>
        <UserPreferredObjectStore
            v-if="isConfigLoaded && config.object_store_allows_id_selection && currentUser"
            :preferred-object-store-id="currentUser.preferred_object_store_id"
            :user-id="userId">
        </UserPreferredObjectStore>
        <UserPreferencesElement
            v-if="hasObjectStoreTemplates"
            id="manage-object-stores"
            class="manage-object-stores"
            :icon="faHdd"
            title="Manage Your Storage Locations"
            description="Add, remove, or update your personally configured storage locations."
            to="/object_store_instances/index" />
        <UserPreferencesElement
            v-if="hasFileSourceTemplates"
            id="manage-file-sources"
            class="manage-file-sources"
            :icon="faFile"
            title="Manage Your Remote File Sources"
            description="Add, remove, or update your personally configured location to find files from and write files to."
            to="/file_source_instances/index" />
        <UserDeletion
            v-if="isConfigLoaded && !config.single_user && config.enable_account_interface"
            :email="email"
            :user-id="userId">
        </UserDeletion>
        <UserPreferencesElement
            v-if="hasLogout"
            id="edit-preferences-sign-out"
            :icon="faSignOutAlt"
            title="Sign Out"
            description="Click here to sign out of all sessions."
            @click="showLogoutModal = true" />
        <b-modal v-model="showDataPrivateModal" title="Datasets are now private" title-class="font-weight-bold" ok-only>
            <span v-localize>
                All of your histories and datasets have been made private. If you'd like to make all *future* histories
                private please use the
            </span>
            <a :href="userPermissionsUrl">User Permissions</a>
            <span v-localize>interface</span>.
        </b-modal>
        <b-modal
            v-model="showLogoutModal"
            title="Sign out"
            title-class="font-weight-bold"
            ok-title="Sign out"
            @ok="signOut">
            <span v-localize> Do you want to continue and sign out of all active sessions? </span>
        </b-modal>
    </b-container>
</template>

<script>
import {
    faBell,
    faCloud,
    faCubes,
    faFile,
    faHdd,
    faIdCardAlt,
    faKey,
    faLock,
    faPalette,
    faSignOutAlt,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";
import { getGalaxyInstance } from "app";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import { mapActions, mapState } from "pinia";
import _l from "utils/localization";
import { userLogoutAll } from "utils/logout";
import QueryStringParsing from "utils/query-string-parsing";
import { withPrefix } from "utils/redirect";
import Vue from "vue";

import { getUserPreferencesModel } from "@/components/User/UserPreferencesModel";
import { useConfig } from "@/composables/config";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";

import UserBeaconSettings from "./UserBeaconSettings";
import UserDeletion from "./UserDeletion";
import UserPreferencesElement from "./UserPreferencesElement";
import UserPreferredObjectStore from "./UserPreferredObjectStore";

import ThemeSelector from "./ThemeSelector.vue";

Vue.use(BootstrapVue);

export default {
    components: {
        UserDeletion,
        UserPreferencesElement,
        ThemeSelector,
        UserBeaconSettings,
        UserPreferredObjectStore,
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
    setup() {
        const { config, isConfigLoaded } = useConfig(true);
        return { config, isConfigLoaded };
    },
    data() {
        return {
            email: "",
            diskUsage: "",
            diskQuota: "",
            messageVariant: null,
            message: null,
            showLogoutModal: false,
            showDataPrivateModal: false,
            toggleTheme: false,
            faBell,
            faCloud,
            faCubes,
            faFile,
            faHdd,
            faIdCardAlt,
            faKey,
            faLock,
            faPalette,
            faSignOutAlt,
            faUsers,
        };
    },
    computed: {
        ...mapState(useUserStore, ["currentUser"]),
        ...mapState(useObjectStoreTemplatesStore, {
            hasObjectStoreTemplates: "hasTemplates",
        }),
        ...mapState(useFileSourceTemplatesStore, {
            hasFileSourceTemplates: "hasTemplates",
        }),
        activePreferences() {
            const userPreferencesEntries = Object.entries(getUserPreferencesModel());
            // Object.entries returns an array of arrays, where the first element
            // is the key (string) and the second is the value (object)
            const enabledPreferences = userPreferencesEntries.filter((f) => !f[1].disabled);
            return Object.fromEntries(enabledPreferences);
        },
        hasLogout() {
            if (this.isConfigLoaded) {
                const Galaxy = getGalaxyInstance();
                return !!Galaxy.session_csrf_token && !this.config.single_user;
            } else {
                return false;
            }
        },
        hasThemes() {
            if (this.isConfigLoaded) {
                const themes = Object.keys(this.config.themes);
                return themes?.length > 1 ?? false;
            } else {
                return false;
            }
        },
        userPermissionsUrl() {
            return withPrefix("/user/permissions");
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
        this.ensureObjectStoreTemplates();
        this.ensureFileSourceTemplates();
    },
    methods: {
        ...mapActions(useObjectStoreTemplatesStore, {
            ensureObjectStoreTemplates: "ensureTemplates",
        }),
        ...mapActions(useFileSourceTemplatesStore, {
            ensureFileSourceTemplates: "ensureTemplates",
        }),
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
            if (
                confirm(
                    _l(
                        "WARNING: This will make all datasets (excluding library datasets) for which you have " +
                            "'management' permissions, in all of your histories " +
                            "private (including archived and purged), and will set permissions such that all " +
                            "of your new data in these histories is created as private.  Any " +
                            "datasets within that are currently shared will need " +
                            "to be re-shared or published.  Are you sure you " +
                            "want to do this?"
                    )
                )
            ) {
                axios.post(withPrefix(`/history/make_private?all_histories=true`)).then(() => {
                    this.showDataPrivateModal = true;
                });
            }
        },
        signOut() {
            userLogoutAll();
        },
    },
};
</script>
