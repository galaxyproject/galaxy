<script setup lang="ts">
import axios from "axios";
import { BAlert, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { isRegisteredUser } from "@/api";
import { getGalaxyInstance } from "@/app";
import { getUserPreferencesModel } from "@/components/User/UserPreferencesModel";
import { useConfig } from "@/composables/config";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { userLogoutAll } from "@/utils/logout";
import QueryStringParsing from "@/utils/query-string-parsing";
import { withPrefix } from "@/utils/redirect";

import Heading from "@/components/Common/Heading.vue";
import ThemeSelector from "@/components/User/ThemeSelector.vue";
import UserBeaconSettings from "@/components/User/UserBeaconSettings.vue";
import UserDeletion from "@/components/User/UserDeletion.vue";
import UserPreferencesElement from "@/components/User/UserPreferencesElement.vue";
import UserPreferredObjectStore from "@/components/User/UserPreferredObjectStore.vue";

const { config, isConfigLoaded } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

console.log(currentUser.value);
const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
const fileSourceTemplatesStore = useFileSourceTemplatesStore();

const messageVariant = ref(null);
const message = ref(null);
const showLogoutModal = ref(false);
const showDataPrivateModal = ref(false);
const toggleTheme = ref(false);

const email = computed(() => (isRegisteredUser(currentUser.value) ? currentUser.value?.email : ""));
const diskQuota = computed(() => currentUser.value?.quota_percent);
const diskUsage = computed(() => currentUser.value?.nice_total_disk_usage);
const activePreferences = computed(() => {
    const userPreferencesEntries = Object.entries(getUserPreferencesModel());
    const enabledPreferences = userPreferencesEntries.filter((f) => "disabled" in f[1] && !f[1].disabled);
    return Object.fromEntries(enabledPreferences);
});
const hasLogout = computed(() => {
    if (isConfigLoaded.value) {
        const Galaxy = getGalaxyInstance();
        return !!Galaxy.session_csrf_token && !config.value.single_user;
    } else {
        return false;
    }
});
const hasThemes = computed(() => {
    if (isConfigLoaded.value) {
        const themes = Object.keys(config.value.themes);
        return themes.length > 1;
    } else {
        return false;
    }
});
const userPermissionsUrl = computed(() => {
    return withPrefix("/user/permissions");
});

function toggleNotifications() {
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
}

function makeDataPrivate() {
    if (
        confirm(
            localize(
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
            showDataPrivateModal.value = true;
        });
    }
}

function signOut() {
    userLogoutAll();
}

onMounted(async () => {
    const msg = QueryStringParsing.get("message");
    const status = QueryStringParsing.get("status");

    if (msg && status) {
        message.value = msg;
        messageVariant.value = status;
    }

    objectStoreTemplatesStore.ensureTemplates();
    fileSourceTemplatesStore.ensureTemplates();
});
</script>

<template>
    <div class="user-preferences">
        <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2"> User Preferences </Heading>
        <BAlert :variant="messageVariant" :show="!!message">
            {{ message }}
        </BAlert>
        <p>
            <span v-localize>You are signed in as</span>
            <strong id="user-preferences-current-email">{{ email }}</strong>
            <span v-localize>and you are using</span>
            <strong>{{ diskUsage }}</strong>
            <span v-localize>of disk space.</span>
            <span v-localize>If this is more than expected, please visit the</span>
            <RouterLink id="edit-preferences-cloud-auth" to="/storage">
                <b v-localize>Storage Dashboard</b>
            </RouterLink>
            <span v-localize>to free up disk space.</span>
            <span v-if="config?.enable_quotas">
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
            icon="fa-users"
            title="Set Dataset Permissions for New Histories"
            description="Grant others default access to newly created histories. Changes made here will only affect histories created after these settings have been stored."
            to="/user/permissions" />
        <UserPreferencesElement
            id="edit-preferences-api-key"
            icon="fa-key"
            title="Manage API Key"
            description="Access your current API key or create a new one."
            to="/user/api_key" />
        <UserPreferencesElement
            id="edit-preferences-notifications"
            icon="fa-bell"
            title="Manage Notifications"
            description="Manage your notification settings."
            to="/user/notifications/preferences" />
        <UserPreferencesElement
            v-if="isConfigLoaded && config.enable_oidc && !config.fixed_delegated_auth"
            id="manage-third-party-identities"
            icon="fa-id-card-o"
            title="Manage Third-Party Identities"
            description="Connect or disconnect access to your third-party identities."
            to="/user/external_ids" />
        <UserPreferencesElement
            id="edit-preferences-custom-builds"
            icon="fa-cubes"
            title="Manage Custom Builds"
            description="Add or remove custom builds using history datasets."
            to="/custom_builds" />
        <UserPreferencesElement
            v-if="hasThemes"
            icon="fa-palette"
            title="Pick a Color Theme"
            description="Click here to change the user interface color theme."
            @click="toggleTheme = !toggleTheme">
            <b-collapse v-model="toggleTheme">
                <ThemeSelector />
            </b-collapse>
        </UserPreferencesElement>
        <UserPreferencesElement
            v-if="isConfigLoaded && !config.single_user"
            id="edit-preferences-make-data-private"
            icon="fa-lock"
            title="Make All Data Private"
            description="Click here to make all data private."
            @click="makeDataPrivate" />
        <UserBeaconSettings v-if="isConfigLoaded && config.enable_beacon_integration" :user-id="currentUser?.id">
        </UserBeaconSettings>
        <UserPreferredObjectStore
            v-if="isConfigLoaded && config.object_store_allows_id_selection && currentUser"
            :preferred-object-store-id="currentUser?.preferred_object_store_id"
            :user-id="currentUser?.id">
        </UserPreferredObjectStore>
        <UserPreferencesElement
            v-if="objectStoreTemplatesStore.hasTemplates"
            id="manage-object-stores"
            class="manage-object-stores"
            icon="fa-hdd"
            title="Manage Your Galaxy Storage"
            description="Add, remove, or update your personally configured Galaxy storage."
            to="/object_store_instances/index" />
        <UserPreferencesElement
            v-if="fileSourceTemplatesStore.hasTemplates"
            id="manage-file-sources"
            class="manage-file-sources"
            icon="fa-file"
            title="Manage Your Repositories"
            description="Add, remove, or update your personally configured location to find files from and write files to."
            to="/file_source_instances/index" />
        <UserDeletion
            v-if="isConfigLoaded && !config.single_user && config.enable_account_interface"
            :email="email"
            :user-id="currentUser?.id || ''">
        </UserDeletion>
        <UserPreferencesElement
            v-if="hasLogout"
            id="edit-preferences-sign-out"
            icon="fa-sign-out"
            title="Sign Out"
            description="Click here to sign out of all sessions."
            @click="showLogoutModal = true" />
        <BModal v-model="showDataPrivateModal" title="Datasets are now private" title-class="font-weight-bold" ok-only>
            <span v-localize>
                All of your histories and datasets have been made private. If you'd like to make all *future* histories
                private please use the
            </span>
            <a :href="userPermissionsUrl">User Permissions</a>
            <span v-localize>interface</span>.
        </BModal>
        <BModal
            v-model="showLogoutModal"
            title="Sign out"
            title-class="font-weight-bold"
            ok-title="Sign out"
            @ok="signOut">
            <span v-localize> Do you want to continue and sign out of all active sessions? </span>
        </BModal>
    </div>
</template>
