<script setup lang="ts">
import { faCaretRight, faPlus, faSave, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BCollapse, BFormGroup } from "bootstrap-vue";
import { faPencil, faSpinner } from "font-awesome-6";
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import { isRegisteredUser } from "@/api";
import type {
    ServiceCredentialPayload,
    ServiceCredentialsDefinition,
    ServiceCredentialsIdentifier,
    ServiceGroupPayload,
    ServiceVariableDefinition,
    UserCredentials,
} from "@/api/users";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { useUserCredentialsStore } from "@/stores/userCredentials";
import { useUserStore } from "@/stores/userStore";

import FormElement from "@/components/Form/FormElement.vue";

type CredentialType = "variable" | "secret";

interface Props {
    credentialDefinition: ServiceCredentialsDefinition;
    credentialPayload: ServiceCredentialPayload;
    isProvidedByUser: boolean;
    sourceData: {
        sourceId: string;
        sourceType: "tool";
        sourceVersion: string;
    };
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update-credentials-list", userCredentials: UserCredentials[]): void;
    (e: "new-credentials-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "update-current-set", credential: ServiceCredentialPayload, newSet: ServiceGroupPayload): void;
    (e: "delete-credentials-group", serviceId: ServiceCredentialsIdentifier, groupName: string): void;
}>();

const { confirm } = useConfirmDialog();

const userStore = useUserStore();
const userCredentialsStore = useUserCredentialsStore(
    isRegisteredUser(userStore.currentUser) ? userStore.currentUser.id : "anonymous"
);

const isBusy = ref(false);
const saveButtonText = ref("Save");
const tmpSet = ref<ServiceGroupPayload | undefined>(undefined);
const originalName = ref<string>();
const isNewSet = ref(false);

const selectedSet = ref<ServiceGroupPayload | undefined>(
    props.credentialPayload.groups.find((group) => group.name === props.credentialPayload.current_group)
);

const isExpanded = ref(false);

const newNameError = ref<string | undefined>(undefined);

// const newSetName = computed<string>({
//     get: () => selectedSet.value?.name ?? "",
//     set: (inputValue) => {
//         if (
//             inputValue.trim() !== "" &&
//             !availableSets.value.some((set) => set.name === inputValue) &&
//             inputValue !== defaultSet.value?.name
//         ) {
//             selectedSet.value!.name = inputValue;
//             newNameError.value = undefined;
//         } else if (inputValue.trim() === "" || inputValue === defaultSet.value?.name) {
//             newNameError.value = "This name is not allowed.";
//         }
//     },
// });
// check tmpSet name instead of selectedSet name
const newSetName = computed<string>({
    get: () => tmpSet.value?.name ?? "",
    set: (inputValue) => {
        if (
            inputValue.trim() !== "" &&
            !availableSets.value.some((set) => set.name === inputValue) &&
            inputValue !== defaultSet.value?.name
        ) {
            tmpSet.value!.name = inputValue;
            newNameError.value = undefined;
        } else {
            newNameError.value = "This name is not allowed.";
        }
    },
});

const setNameHelp = computed<string>(() => {
    // if (selectedSet.value?.name === defaultSet.value?.name) {
    //     return "The default set cannot be renamed.";
    // }

    return `Enter a name for the set of credentials for ${serviceName.value}`;
});

const hasNameConflict = computed<boolean>(() => {
    return newSetName.value.trim() !== "" && availableSets.value.some((set) => set.name === newSetName.value);
});

const serviceName = computed<string>(() => props.credentialDefinition.label || props.credentialDefinition.name);

const availableSets = computed<ServiceGroupPayload[]>(() => Object.values(props.credentialPayload.groups));

const canCreateNewSet = computed<boolean>(
    () =>
        selectedSet.value?.name.trim() !== "" &&
        !availableSets.value.some((set) => set.name === selectedSet.value?.name)
);

const canDeleteSet = computed<boolean>(() => selectedSet.value?.name !== defaultSet.value?.name ?? false);

const defaultSet = computed<ServiceGroupPayload | undefined>(() =>
    availableSets.value.find((set) => set.name === "default")
);

function generateUniqueName(template: string, sets: ServiceGroupPayload[]): string {
    let name = template;
    let counter = 1;
    while (sets.some((set) => set.name === name)) {
        name = `${template} ${counter}`;
        counter++;
    }
    return name;
}

function getVariableDefinition(name: string, type: CredentialType): ServiceVariableDefinition {
    const definition = props.credentialDefinition[type === "variable" ? "variables" : "secrets"].find(
        (variable) => variable.name === name
    );
    if (!definition) {
        throw new Error(`Variable definition not found for variable ${name}`);
    }
    return definition;
}

function getVariableTitle(name: string, type: CredentialType): string {
    return getVariableDefinition(name, type).label || name;
}

function getVariableDescription(name: string, type: CredentialType): string | undefined {
    return getVariableDefinition(name, type).description;
}

function isVariableOptional(name: string, type: CredentialType): boolean {
    return getVariableDefinition(name, type).optional;
}

function onCreateNewSet() {
    const newSet: ServiceGroupPayload = {
        name: generateUniqueName("new credential", props.credentialPayload.groups),
        variables: selectedSet.value?.variables.map((variable) => ({ ...variable, value: null })) || [],
        secrets: selectedSet.value?.secrets.map((secret) => ({ ...secret, value: null, alreadySet: false })) || [],
    };

    console.log("Creating new set of credentials", newSet);

    // emit("new-credentials-set", props.credentialPayload, newSet);
    tmpSet.value = newSet;
    // onCurrentSetChange(newSet);

    isNewSet.value = true;

    toggleEditingMode(true);
}

function onCurrentSetChange(selectedSet: ServiceGroupPayload) {
    emit("update-current-set", props.credentialPayload, selectedSet);
}

const editMode = ref(false);

function toggleEditingMode(state: boolean) {
    editMode.value = state;

    if (!state) {
        tmpSet.value = undefined;
        isNewSet.value = false;
    }
}

async function onDeleteSet() {
    const confirmed = await confirm("Are you sure you want to delete this set of credentials?", {
        title: "Delete credentials set",
        okTitle: "Delete set",
        okVariant: "danger",
        cancelVariant: "outline-primary",
    });

    if (confirmed && selectedSet.value) {
        const groupNameToDelete = selectedSet.value.name;
        const defaultSet = availableSets.value.find((set) => set.name === "default");

        if (defaultSet) {
            selectedSet.value = defaultSet;
            onCurrentSetChange(defaultSet);
        }

        emit("delete-credentials-group", props.credentialPayload, groupNameToDelete);
    }
}

function onDiscardSet() {
    selectedSet.value = availableSets.value.find((set) => set.name === props.credentialPayload.current_group);
    toggleEditingMode(false);
}

function onEditSet() {
    tmpSet.value = undefined;
    tmpSet.value = { ...selectedSet.value! };
    originalName.value = tmpSet.value!.name;

    isNewSet.value = false;

    toggleEditingMode(true);
}

async function onSaveSet() {
    // if (newNameError.value) {
    //     return;
    // }

    // if (selectedSet.value) {
    //     emit("update-current-set", props.credentialPayload, selectedSet.value);
    // }

    // toggleEditingMode(false);

    saveButtonText.value = "Saving";
    // tmpSet

    try {
        isBusy.value = true;
        console.log("Saving user credentials");

        const toSend = {
            source_id: props.sourceData.sourceId,
            source_type: props.sourceData.sourceType,
            source_version: props.sourceData.sourceVersion,
            credentials: [{ ...props.credentialPayload, groups: [tmpSet.value!] }],
        };

        const newData = await userCredentialsStore.saveUserCredentialsForTool(toSend);

        emit("update-credentials-list", newData);
        toggleEditingMode(false);
    } catch (error) {
        // TODO: Implement error handling.
        console.error("Error saving user credentials", error);
    } finally {
        isBusy.value = false;
    }
}
</script>

<template>
    <div>
        <div>
            <BButton class="service-title" block variant="outline-info" @click="isExpanded = !isExpanded">
                <span>
                    <FontAwesomeIcon v-if="!isExpanded" :icon="faCaretRight" />
                    <FontAwesomeIcon v-else :icon="faCaretRight" rotation="90" />
                    {{ serviceName }}
                </span>

                <span class="text-muted selected-set-info">
                    <span v-if="!isProvidedByUser"> No credentials set</span>
                    <span v-else-if="selectedSet">
                        Using: <b>{{ selectedSet.name }}</b>
                    </span>
                </span>
            </BButton>
        </div>

        <BCollapse :id="`accordion-${credentialDefinition.name}`" v-model="isExpanded">
            <form autocomplete="off" class="credentials-form">
                <p>{{ credentialDefinition.description }}</p>

                <div class="set-actions">
                    <BFormGroup
                        description="This is the current set of credentials you are using for this service. You can switch between sets or create a new one.">
                        <Multiselect
                            v-model="selectedSet"
                            :options="availableSets"
                            :label="`name`"
                            :track-by="`name`"
                            :allow-empty="false"
                            :show-labels="false"
                            :disabled="editMode"
                            :placeholder="`Select ${serviceName} set`"
                            @input="onCurrentSetChange" />
                    </BFormGroup>

                    <BButtonGroup>
                        <BButton
                            v-b-tooltip.hover.noninteractive
                            :disabled="!canDeleteSet"
                            variant="outline-danger"
                            size="sm"
                            title="Delete selected set"
                            @click="onDeleteSet">
                            <FontAwesomeIcon :icon="faTrash" />
                        </BButton>

                        <BButton
                            v-b-tooltip.hover.noninteractive
                            variant="outline-info"
                            size="sm"
                            title="Edit selected set"
                            @click="onEditSet">
                            <FontAwesomeIcon :icon="faPencil" />
                        </BButton>

                        <BButton
                            v-b-tooltip.hover.noninteractive
                            :disabled="canCreateNewSet"
                            variant="outline-info"
                            size="sm"
                            title="Create a new set of credentials"
                            @click="onCreateNewSet">
                            <FontAwesomeIcon :icon="faPlus" />
                        </BButton>
                    </BButtonGroup>
                </div>

                <BCollapse v-if="tmpSet" :visible="editMode" class="set-body">
                    <div class="d-flex justify-content-between">
                        <span v-if="isNewSet">
                            New set: <b>{{ originalName }}</b>
                        </span>
                        <span v-else v-once>
                            Editing set: <b>{{ tmpSet.name }}</b>
                        </span>

                        <div class="d-flex justify-content-center flex-gapx-1">
                            <BButton
                                v-b-tooltip.hover.noninteractive
                                variant="outline-danger"
                                size="sm"
                                title="Discard changes to this set"
                                @click="onDiscardSet">
                                Discard
                            </BButton>

                            <BButton
                                v-b-tooltip.hover.noninteractive
                                variant="outline-info"
                                size="sm"
                                :title="saveButtonText"
                                :disabled="!!newNameError || isBusy"
                                @click="onSaveSet">
                                <FontAwesomeIcon :icon="isBusy ? faSpinner : faSave" :spin="isBusy" />
                                {{ saveButtonText }}
                            </BButton>
                        </div>
                    </div>

                    <div class="p-2">
                        <FormElement
                            v-if="tmpSet?.name !== defaultSet?.name"
                            v-model="newSetName"
                            type="text"
                            title="Set name"
                            :warning="newNameError"
                            :optional="false"
                            :help="setNameHelp" />

                        <div v-for="variable in tmpSet.variables" :key="variable.name">
                            <FormElement
                                :id="`${tmpSet.name}-${variable.name}-variable`"
                                v-model="variable.value"
                                type="text"
                                :title="getVariableTitle(variable.name, 'variable')"
                                :optional="isVariableOptional(variable.name, 'variable')"
                                :help="getVariableDescription(variable.name, 'variable')" />
                        </div>

                        <div v-for="secret in tmpSet.secrets" :key="secret.name" class="secret-input">
                            <FormElement
                                :id="`${tmpSet.name}-${secret.name}-secret`"
                                v-model="secret.value"
                                type="password"
                                :autocomplete="`${tmpSet.name}-${secret.name}-secret`"
                                :title="getVariableTitle(secret.name, 'secret')"
                                :optional="isVariableOptional(secret.name, 'secret')"
                                :help="getVariableDescription(secret.name, 'secret')" />
                        </div>
                    </div>
                </BCollapse>
            </form>
        </BCollapse>
    </div>
</template>

<style scoped lang="scss">
@import "scss/theme/blue.scss";

.service-title {
    font-size: 1rem;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    text-align: left;
}

.selected-set-info {
    font-size: 0.8rem;
    font-weight: normal;
    align-self: center;
}

.set-actions {
    display: flex;
    justify-content: space-between;

    button {
        margin-left: 0.5rem;
        align-self: baseline;
        padding: 9px;
    }
}

.set-body {
    border: 1px solid $gray-300;
    border-radius: 0.25rem;
    padding: 1rem;
}

.credentials-form {
    border-radius: 0 0 0.25rem 0.25rem;
    border: 1px solid $gray-300;
    border-top: none;
    padding: 1rem;
}

.secret-input {
    display: flex;
    align-items: center;
}
</style>
