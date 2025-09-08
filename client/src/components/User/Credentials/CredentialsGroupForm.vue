<script setup lang="ts">
import { BFormGroup, BFormInput } from "bootstrap-vue";
import { computed } from "vue";

import type { CredentialType } from "@/api/userCredentials";
import type { ServiceCredentialsDefinition, ServiceGroupPayload, ServiceParameterDefinition } from "@/api/users";

interface EditGroup {
    groupId: string;
    isNewGroup: boolean;
    groupPayload: ServiceGroupPayload;
}

interface Props {
    groupData: EditGroup;
    serviceDefinition: ServiceCredentialsDefinition;
}

const props = defineProps<Props>();

const groupName = computed<string>({
    get(): string {
        return props.groupData.groupPayload?.name || "";
    },
    set(value: string): void {
        if (props.groupData) {
            const trimmedValue = String(value || "").trim();
            (props.groupData.groupPayload as any).name = trimmedValue;
        }
    },
});

function getGroupNameState(): boolean | null {
    const name = groupName.value;
    if (!name) {
        return false;
    }
    if (name.length < 3) {
        return false;
    }
    return true;
}

function getGroupNameErrorMessage(): string | null {
    const name = groupName.value;
    if (!name) {
        return "Group name is required";
    }
    if (name.length < 3) {
        return "Group name must be at least 3 characters";
    }
    return null;
}

function getFieldId(fieldName: string, type: CredentialType): string {
    return `${props.groupData.groupId}-${fieldName}-${type}`;
}

function getInputId(fieldName: string, type: CredentialType): string {
    return `${getFieldId(fieldName, type)}-input`;
}

function getVariableDefinition(name: string, type: CredentialType): ServiceParameterDefinition {
    const definitions = type === "variable" ? props.serviceDefinition.variables : props.serviceDefinition.secrets;
    const definition = definitions.find((variable) => variable.name === name);

    if (!definition) {
        throw new Error(`Variable definition not found for ${type} "${name}"`);
    }

    return definition;
}

function getVariableTitle(name: string, type: CredentialType): string {
    const definition = getVariableDefinition(name, type);
    return definition.label || name;
}

function getVariableDescription(name: string, type: CredentialType): string | undefined {
    const definition = getVariableDefinition(name, type);
    return definition.description;
}

function isVariableOptional(name: string, type: CredentialType): boolean {
    const definition = getVariableDefinition(name, type);
    return definition.optional;
}

function getFieldState(value: string | null | undefined, name: string, type: CredentialType): boolean | null {
    if (!value) {
        return isVariableOptional(name, type) ? null : false;
    }
    return true;
}
</script>

<template>
    <div class="p-2">
        <span v-if="props.groupData.isNewGroup"> Creating new group of credentials </span>
        <span v-else> Editing credentials group </span>

        <BFormGroup
            :id="`${props.groupData.groupId}-name`"
            label="Group Name"
            description="Enter a unique name for this group"
            :invalid-feedback="getGroupNameErrorMessage()">
            <BFormInput
                :id="`${props.groupData.groupId}-name-input`"
                v-model="groupName"
                type="text"
                :state="getGroupNameState()"
                placeholder="Enter group name"
                title="Group Name"
                aria-label="Group Name"
                class="mb-2" />
        </BFormGroup>

        <div v-for="variable in props.groupData.groupPayload.variables" :key="getFieldId(variable.name, 'variable')">
            <BFormGroup
                :id="getFieldId(variable.name, 'variable')"
                :label="getVariableTitle(variable.name, 'variable')"
                :description="getVariableDescription(variable.name, 'variable')">
                <BFormInput
                    :id="getInputId(variable.name, 'variable')"
                    v-model="variable.value"
                    type="text"
                    :state="getFieldState(variable.value, variable.name, 'variable')"
                    :placeholder="getVariableTitle(variable.name, 'variable')"
                    :title="getVariableTitle(variable.name, 'variable')"
                    :aria-label="getVariableTitle(variable.name, 'variable')"
                    :required="!isVariableOptional(variable.name, 'variable')"
                    :readonly="false"
                    class="mb-2" />
            </BFormGroup>
        </div>

        <div v-for="secret in props.groupData.groupPayload.secrets" :key="getFieldId(secret.name, 'secret')">
            <BFormGroup
                :id="getFieldId(secret.name, 'secret')"
                :label="getVariableTitle(secret.name, 'secret')"
                :description="getVariableDescription(secret.name, 'secret')">
                <BFormInput
                    :id="getInputId(secret.name, 'secret')"
                    v-model="secret.value"
                    type="password"
                    autocomplete="off"
                    :state="getFieldState(secret.value, secret.name, 'secret')"
                    :placeholder="getVariableTitle(secret.name, 'secret')"
                    :title="getVariableTitle(secret.name, 'secret')"
                    :aria-label="getVariableTitle(secret.name, 'secret')"
                    :required="!isVariableOptional(secret.name, 'secret')"
                    :readonly="false"
                    class="mb-2" />
            </BFormGroup>
        </div>
    </div>
</template>
