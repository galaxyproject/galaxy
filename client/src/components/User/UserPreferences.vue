<script setup lang="ts">
import axios from "axios";
import { BAlert, BModal } from "bootstrap-vue";
import {
    faBell,
    faBroadcastTower,
    faCubes,
    faFile,
    faHdd,
    faIdCard,
    faKey,
    faLock,
    faPalette,
    faRadiation,
    faSignOut,
    faUsers,
} from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, onMounted, ref } from "vue";

import { getGalaxyInstance } from "@/app";
import { getUserPreferencesModel } from "@/components/User/UserPreferencesModel";
import { useConfig } from "@/composables/config";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useFileSourceTemplatesStore } from "@/stores/fileSourceTemplatesStore";
import { useObjectStoreTemplatesStore } from "@/stores/objectStoreTemplatesStore";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { userLogoutAll } from "@/utils/logout";
import QueryStringParsing from "@/utils/query-string-parsing";
import { withPrefix } from "@/utils/redirect";

import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import UserBeaconSettings from "@/components/User/UserBeaconSettings.vue";
import UserDeletion from "@/components/User/UserDeletion.vue";
import UserDetailsElement from "@/components/User/UserDetailsElement.vue";
import UserPickTheme from "@/components/User/UserPickTheme.vue";
import UserPreferencesElement from "@/components/User/UserPreferencesElement.vue";
import UserPreferredObjectStore from "@/components/User/UserPreferredObjectStore.vue";

const breadcrumbItems = [{ title: "User Preferences" }];

const { confirm } = useConfirmDialog();

const { config, isConfigLoaded } = useConfig(true);

const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);

const objectStoreTemplatesStore = useObjectStoreTemplatesStore();
const fileSourceTemplatesStore = useFileSourceTemplatesStore();

const messageVariant = ref(null);
const message = ref(null);
const showBeaconModal = ref(false);
const showPreferredStorageModal = ref(false);
const showDeleteAccountModal = ref(false);
const showDataPrivateModal = ref(false);
const showThemPickerModal = ref(false);

const activePreferences = computed(() => {
    const userPreferencesEntries = getUserPreferencesModel();
    const enabledPreferences = Object.entries(userPreferencesEntries).filter(([, value]) => !value.disabled);
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

async function makeDataPrivate() {
    const confirmed = await confirm(
        localize(
            "WARNING: This will make all datasets (excluding library datasets) for which you have " +
                "'management' permissions, in all of your histories " +
                "private (including archived and purged), and will set permissions such that all " +
                "of your new data in these histories is created as private.  Any " +
                "datasets within that are currently shared will need " +
                "to be re-shared or published.  Are you sure you " +
                "want to do this?"
        ),
        {
            title: "Do you want to make all data private?",
            okTitle: "Yes, make all data private",
            cancelTitle: "No, do not make data private",
            cancelVariant: "outline-primary",
            centered: true,
        }
    );
    if (confirmed) {
        axios.post(withPrefix(`/history/make_private?all_histories=true`)).then(() => {
            showDataPrivateModal.value = true;
        });
    }
}

async function signOut() {
    const confirmed = await confirm(localize("Do you want to continue and sign out of all active sessions?"), {
        title: "Sign out of all sessions",
        okTitle: "Yes, sign out",
        okVariant: "danger",
        cancelTitle: "Cancel",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed) {
        userLogoutAll();
    }
}

function toggleThemeModal() {
    showThemPickerModal.value = !showThemPickerModal.value;
}

function toggleBeaconModal() {
    showBeaconModal.value = !showBeaconModal.value;
}

function togglePreferredStorageModal() {
    showPreferredStorageModal.value = !showPreferredStorageModal.value;
}

function toggleUserDeletion() {
    showDeleteAccountModal.value = !showDeleteAccountModal.value;
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
    <div class="d-flex flex-column">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <Heading h2 size="md">
            This page allows you to manage your user preferences. You can change your email address, password, and other
            settings here.
        </Heading>

        <BAlert :variant="messageVariant" :show="!!message">
            {{ message }}
        </BAlert>

        <UserDetailsElement />

        <div class="d-flex flex-gapy-1 flex-column">
            <div class="d-flex flex-wrap mb-4 user-preferences-cards">
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
                    title="Manage Galaxy API Key"
                    description="Access your current Galaxy API key or create a new one."
                    to="/user/api_key" />

                <UserPreferencesElement
                    id="edit-preferences-notifications"
                    :icon="faBell"
                    title="Manage Notifications"
                    description="Manage your notification settings."
                    to="/user/notifications/preferences" />

                <UserPreferencesElement
                    v-if="isConfigLoaded && config.enable_oidc && !config.fixed_delegated_auth"
                    id="manage-third-party-identities"
                    :icon="faIdCard"
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
                    id="edit-preferences-theme"
                    :icon="faPalette"
                    title="Pick a Color Theme"
                    description="Click here to change the user interface color theme."
                    @click="toggleThemeModal" />

                <UserPreferencesElement
                    v-if="isConfigLoaded && !config.single_user"
                    id="edit-preferences-make-data-private"
                    :icon="faLock"
                    title="Make All Data Private"
                    description="Click here to make all data private."
                    @click="makeDataPrivate" />

                <UserPreferencesElement
                    v-if="isConfigLoaded && config.enable_beacon_integration"
                    id="edit-preferences-beacon"
                    :icon="faBroadcastTower"
                    title="Manage Beacon"
                    description="Contribute variants to Beacon"
                    @click="toggleBeaconModal" />

                <UserPreferencesElement
                    v-if="isConfigLoaded && config.object_store_allows_id_selection && currentUser"
                    id="manage-preferred-object-store"
                    :icon="faHdd"
                    title="Manage Your Preferred Galaxy Storage"
                    description="Select a Preferred Galaxy storage for the outputs of new jobs."
                    @click="togglePreferredStorageModal" />

                <UserPreferencesElement
                    v-if="objectStoreTemplatesStore.hasTemplates"
                    id="manage-object-stores"
                    class="manage-object-stores"
                    :icon="faHdd"
                    title="Manage Your Galaxy Storage"
                    description="Add, remove, or update your personally configured Galaxy storage."
                    to="/object_store_instances/index" />

                <UserPreferencesElement
                    v-if="fileSourceTemplatesStore.hasTemplates"
                    id="manage-file-sources"
                    class="manage-file-sources"
                    :icon="faFile"
                    title="Manage Your Repositories"
                    description="Add, remove, or update your personally configured location to find files from and write files to."
                    to="/file_source_instances/index" />
            </div>

            <div class="d-flex flex-wrap mb-4 user-preferences-cards">
                <UserPreferencesElement
                    v-if="isConfigLoaded && !config.single_user && config.enable_account_interface"
                    id="delete-account"
                    danger-zone
                    :icon="faRadiation"
                    title="Delete Account"
                    description="Click here to delete your account."
                    @click="toggleUserDeletion" />

                <UserPreferencesElement
                    v-if="hasLogout"
                    id="edit-preferences-sign-out"
                    danger-zone
                    :icon="faSignOut"
                    title="Sign Out of All Sessions"
                    description="Click here to sign out of all sessions."
                    @click="signOut" />
            </div>

            <BModal
                v-model="showDataPrivateModal"
                title="Datasets are now private"
                title-class="font-weight-bold"
                ok-only>
                <span v-localize>
                    All of your histories and datasets have been made private. If you'd like to make all *future*
                    histories private please use the
                </span>
                <a :href="userPermissionsUrl">User Permissions</a>
                <span v-localize>interface</span>.
            </BModal>

            <UserPickTheme v-if="hasThemes && showThemPickerModal" @reset="toggleThemeModal" />

            <UserBeaconSettings
                v-if="isConfigLoaded && config.enable_beacon_integration && showBeaconModal"
                @reset="toggleBeaconModal" />

            <UserPreferredObjectStore
                v-if="isConfigLoaded && config.object_store_allows_id_selection && showPreferredStorageModal"
                @reset="togglePreferredStorageModal" />

            <UserDeletion v-if="showDeleteAccountModal" @reset="toggleUserDeletion" />
        </div>
    </div>
</template>

<style scoped lang="scss">
.user-preferences-cards {
    container: cards-list / inline-size;
}
</style>
