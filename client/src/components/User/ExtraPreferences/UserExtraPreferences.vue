<script setup lang="ts">
import { faSave, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { GalaxyApi, isRegisteredUser } from "@/api";
import type { FormData } from "@/components/Form/composables/useFormState";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    buildClearPayload,
    buildInputs,
    buildPayload,
    type ClearableSecret,
    clearableSecrets,
    type ExtraPreferenceSection,
    type ExtraPreferencesPayload,
    type ExtraPreferenceValues,
    isSecretMissing,
} from "./extraPreferencesForm";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

// The app reads these sections at startup, so a change only shows after a reload.
const STARTUP_SECTIONS = ["localization", "sentry_replay"];

const breadcrumbItems = [{ title: "User Preferences", to: "/user" }, { title: "Extra Configurations" }];

const { confirm } = useConfirmDialog();
const { currentUser } = storeToRefs(useUserStore());

const userId = computed(() => (isRegisteredUser(currentUser.value) && currentUser.value.id) || "");

const definition = ref<ExtraPreferenceSection[]>([]);
const values = ref<ExtraPreferenceValues>({});
const formData = ref<FormData>({});
// FormDisplay only resets its values when its id changes.
const formId = ref(0);
const validation = ref<[string, string] | null>(null);

const loading = ref(true);
const saving = ref(false);
const loadError = ref("");
const saveError = ref("");
const saved = ref(false);

const inputs = computed(() => buildInputs(definition.value, values.value));
const payload = computed(() => buildPayload(definition.value, values.value, formData.value));
const secrets = computed(() => clearableSecrets(definition.value, values.value));
const canSave = computed(
    () =>
        Object.keys(payload.value).length > 0 &&
        !validation.value &&
        !isSecretMissing(definition.value, values.value, formData.value) &&
        !saving.value,
);

async function load(id: string) {
    loading.value = true;
    loadError.value = "";
    const [definitionResponse, valuesResponse] = await Promise.all([
        GalaxyApi().GET("/api/configuration/extra_preferences"),
        GalaxyApi().GET("/api/users/{user_id}/extra_preferences", { params: { path: { user_id: id } } }),
    ]);
    if (definitionResponse.error || valuesResponse.error) {
        loadError.value = errorMessageAsString(
            definitionResponse.error ?? valuesResponse.error,
            "Failed to load the extra configurations.",
        );
    } else {
        // the generated tuple types of the select options widen to arrays
        definition.value = definitionResponse.data as ExtraPreferenceSection[];
        values.value = valuesResponse.data;
    }
    loading.value = false;
}

/** Sends the payload and shows the values the server stored in return. */
async function send(update: ExtraPreferencesPayload) {
    saving.value = true;
    saveError.value = "";
    saved.value = false;
    const { data, error } = await GalaxyApi().PUT("/api/users/{user_id}/extra_preferences", {
        params: { path: { user_id: userId.value } },
        body: update,
    });
    if (error) {
        saveError.value = errorMessageAsString(error, "Failed to save the extra configurations.");
    } else {
        values.value = data;
        formId.value++;
        saved.value = true;
        if (Object.keys(update).some((section) => STARTUP_SECTIONS.includes(section))) {
            window.location.reload();
        }
    }
    saving.value = false;
}

async function clearSecret(secret: ClearableSecret) {
    const confirmed = await confirm(`Remove the stored value of "${secret.label}" in "${secret.sectionLabel}"?`, {
        title: "Remove stored value",
        okText: "Remove",
        okColor: "red",
    });
    if (confirmed) {
        await send(buildClearPayload(secret.section, secret.name));
    }
}

function onChange(data: FormData) {
    formData.value = data;
}

watch(
    userId,
    (id) => {
        if (id) {
            load(id);
        }
    },
    { immediate: true },
);
</script>

<template>
    <div id="user-extra-preferences">
        <BreadcrumbHeading :items="breadcrumbItems" />

        <GAlert v-if="loadError" variant="danger" show>{{ loadError }}</GAlert>
        <GAlert v-else-if="loading" show>
            <LoadingSpan message="Loading extra configurations" />
        </GAlert>
        <GAlert v-else-if="!definition.length" variant="info" show>
            No extra configurations are defined on this Galaxy.
        </GAlert>
        <template v-else>
            <GAlert v-if="saveError" variant="danger" show dismissible @dismissed="saveError = ''">
                {{ saveError }}
            </GAlert>
            <GAlert v-if="saved" variant="success" show dismissible @dismissed="saved = false">
                Extra configurations saved.
            </GAlert>

            <FormDisplay
                :id="String(formId)"
                :inputs="inputs"
                reject-empty-required-inputs
                @on-change="onChange"
                @on-validation="validation = $event" />

            <div v-if="secrets.length" class="extra-preferences-actions" data-description="stored secrets">
                <GButton
                    v-for="secret in secrets"
                    :key="`${secret.section}|${secret.name}`"
                    :disabled="saving"
                    :data-description="`clear ${secret.section}|${secret.name}`"
                    @click="clearSecret(secret)">
                    <FontAwesomeIcon :icon="faTrash" />
                    Remove stored {{ secret.label }} ({{ secret.sectionLabel }})
                </GButton>
            </div>

            <div class="extra-preferences-actions">
                <GButton id="save-extra-preferences" color="blue" :disabled="!canSave" @click="send(payload)">
                    <FontAwesomeIcon :icon="faSave" />
                    Save
                </GButton>
            </div>
        </template>
    </div>
</template>

<style scoped>
.extra-preferences-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-top: 1rem;
}
</style>
