<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormGroup, BFormInput } from "bootstrap-vue";
import { faIdCard, faUnlockAlt } from "font-awesome-6";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import { useConfig } from "@/composables/config";
import { useToast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "@/components/BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import Heading from "@/components/Common/Heading.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Account" }];

const { config, isConfigLoaded } = useConfig(true);
const userStore = useUserStore();
const { currentUser } = storeToRefs(userStore);
const Toast = useToast();

const email = ref("");
const username = ref("");
const displayName = ref("");
const saving = ref(false);
const errorMessage = ref("");

/**
 * Mirrors the server's own `allow_profile_edit`: instances that delegate
 * accounts elsewhere must not offer fields the backend will refuse to save.
 */
const canEdit = computed(
    () =>
        isConfigLoaded.value &&
        Boolean(config.value.enable_account_interface) &&
        !config.value.use_remote_user &&
        !config.value.disable_local_accounts,
);

const showIdentities = computed(
    () => isConfigLoaded.value && Boolean(config.value.enable_oidc) && !config.value.fixed_delegated_auth,
);

const profilePath = computed(() => (username.value ? `/u/${username.value}` : "/u/your-username"));

const dirty = computed(
    () =>
        isRegisteredUser(currentUser.value) &&
        (email.value !== currentUser.value.email ||
            username.value !== (currentUser.value.username ?? "") ||
            displayName.value !== (currentUser.value.display_name ?? "")),
);

function resetFromUser() {
    if (isRegisteredUser(currentUser.value)) {
        email.value = currentUser.value.email;
        username.value = currentUser.value.username ?? "";
        displayName.value = currentUser.value.display_name ?? "";
    }
}

async function onSubmit() {
    if (!isRegisteredUser(currentUser.value) || saving.value) {
        return;
    }

    saving.value = true;
    errorMessage.value = "";

    // Only changed fields are sent: the server treats an email change as a
    // re-verification, so resending the current address would deactivate the
    // account for no reason.
    const body: Record<string, string> = {};
    if (email.value !== currentUser.value.email) {
        body.email = email.value;
    }
    if (username.value !== (currentUser.value.username ?? "")) {
        body.username = username.value;
    }
    if (displayName.value !== (currentUser.value.display_name ?? "")) {
        body.display_name = displayName.value;
    }

    try {
        const { error } = await GalaxyApi().PUT("/api/users/{user_id}", {
            params: { path: { user_id: currentUser.value.id } },
            body,
        });

        if (error) {
            errorMessage.value = errorMessageAsString(error);
            return;
        }

        await userStore.refreshUser();
        resetFromUser();
        Toast.success(localize("Your account details have been saved."));
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        saving.value = false;
    }
}

watch(currentUser, resetFromUser, { immediate: true });
</script>

<template>
    <div>
        <BreadcrumbHeading :items="breadcrumbItems" />

        <BAlert v-if="!isRegisteredUser(currentUser)" show>
            <LoadingSpan message="Loading your account" />
        </BAlert>

        <form v-else @submit.prevent="onSubmit">
            <BAlert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </BAlert>

            <BAlert v-if="!canEdit" show variant="info">
                <span v-localize>
                    Your account details are managed outside Galaxy on this instance, so they cannot be edited here.
                </span>
            </BAlert>

            <section class="user-information-section">
                <Heading v-localize h2 size="sm">Identity</Heading>

                <BFormGroup label-for="display_name" :label="localize('Display name')">
                    <BFormInput id="display_name" v-model="displayName" :disabled="!canEdit" :placeholder="username" />

                    <small v-localize class="form-text text-muted">
                        Shown in place of your username across Galaxy. Leave it blank to use your username.
                    </small>
                </BFormGroup>

                <BFormGroup label-for="username" :label="localize('Username')">
                    <BFormInput id="username" v-model="username" :disabled="!canEdit" />

                    <small class="form-text text-muted">
                        <span v-localize>
                            Signs you in, and appears in the links you share. Lower-case letters, numbers, '.', '_' and
                            '-' only.
                        </span>

                        <br />

                        <span class="user-information-example">{{ profilePath }}/w/my-workflow</span>
                    </small>

                    <BAlert v-if="username !== (currentUser.username ?? '')" show variant="warning" class="mt-2">
                        <span v-localize>
                            Changing your username breaks links you have already shared - the old addresses stop
                            resolving.
                        </span>
                    </BAlert>
                </BFormGroup>
            </section>

            <section class="user-information-section">
                <Heading v-localize h2 size="sm">Sign-in</Heading>

                <BFormGroup label-for="email" :label="localize('Email address')">
                    <BFormInput id="email" v-model="email" type="email" :disabled="!canEdit" />

                    <small v-localize class="form-text text-muted">
                        Used to sign in and to recover your account.
                    </small>

                    <BAlert
                        v-if="config.user_activation_on && email !== currentUser.email"
                        show
                        variant="warning"
                        class="mt-2">
                        <span v-localize>
                            Changing your email address deactivates your account until you follow the activation link
                            sent to the new address.
                        </span>
                    </BAlert>
                </BFormGroup>

                <div v-if="canEdit" class="user-information-link">
                    <GLink to="/user/password">
                        <FontAwesomeIcon :icon="faUnlockAlt" />
                        <span v-localize>Change password</span>
                    </GLink>
                </div>

                <div v-if="showIdentities" class="user-information-link">
                    <GLink to="/user/external_ids">
                        <FontAwesomeIcon :icon="faIdCard" />
                        <span v-localize>Manage third-party identities</span>
                    </GLink>
                </div>
            </section>

            <div v-if="canEdit" class="d-flex gap-1">
                <GButton id="submit" color="blue" type="submit" :disabled="!dirty || saving">
                    <span v-localize>Save</span>
                </GButton>

                <GButton id="cancel" :disabled="!dirty || saving" @click="resetFromUser">
                    <span v-localize>Cancel</span>
                </GButton>
            </div>
        </form>
    </div>
</template>

<style scoped lang="scss">
.user-information-section {
    margin-bottom: 1.5rem;
    max-width: 40rem;
}

.user-information-example {
    font-family: monospace;
}

.user-information-link {
    margin-bottom: 0.5rem;
}
</style>
