<script setup lang="ts">
/**
 * CredentialsGroupForm Component
 *
 * A form component for creating and editing service credential groups.
 * Provides input fields for group name, variables, and secrets with
 * validation and proper field types.
 *
 * Features:
 * - Group name input with validation
 * - Dynamic variable and secret fields
 * - Field validation and state management
 * - Required/optional field handling
 * - Password masking for secrets
 * - Descriptive labels and placeholders
 * - Real-time validation feedback
 *
 * @component CredentialsGroupForm
 * @example
 * <CredentialsGroupForm
 *   :group-data="editGroup"
 *   :service-definition="serviceDefinition" />
 */

import { BFormGroup, BFormInput } from "bootstrap-vue";
import { computed } from "vue";

import type {
    CredentialType,
    ServiceCredentialGroupPayload,
    ServiceCredentialsDefinition,
    ServiceParameterDefinition,
} from "@/api/userCredentials";

/**
 * Edit group structure for form data
 * @interface EditGroup
 */
interface EditGroup {
    /** Group ID being edited */
    groupId: string;
    /** Whether this is a new group being created */
    isNewGroup: boolean;
    /** Group payload data */
    groupPayload: ServiceCredentialGroupPayload;
}

interface Props {
    /**
     * Group data being edited
     * @type {EditGroup}
     */
    groupData: EditGroup;

    /**
     * Service definition configuration
     * @type {ServiceCredentialsDefinition}
     */
    serviceDefinition: ServiceCredentialsDefinition;
}

const props = defineProps<Props>();

/**
 * Computed property for group name with getter/setter
 * @returns {string} Current group name
 */
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

/**
 * Validates group name and returns field state
 * @returns {boolean | null} Validation state - true if valid, false if invalid, null if neutral
 */
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

/**
 * Gets error message for group name validation
 * @returns {string | null} Error message or null if valid
 */
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

/**
 * Generates a unique field ID for form elements
 * @param {string} fieldName - Name of the field
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {string} Unique field ID
 */
function getFieldId(fieldName: string, type: CredentialType): string {
    return `${props.groupData.groupId}-${fieldName}-${type}`;
}

/**
 * Generates a unique input ID for form input elements
 * @param {string} fieldName - Name of the field
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {string} Unique input ID
 */
function getInputId(fieldName: string, type: CredentialType): string {
    return `${getFieldId(fieldName, type)}-input`;
}

/**
 * Gets the parameter definition for a variable or secret
 * @param {string} name - Parameter name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {ServiceParameterDefinition} Parameter definition
 * @throws {Error} When parameter definition is not found
 */
function getVariableDefinition(name: string, type: CredentialType): ServiceParameterDefinition {
    const definitions = type === "variable" ? props.serviceDefinition.variables : props.serviceDefinition.secrets;
    const definition = definitions.find((variable) => variable.name === name);

    if (!definition) {
        throw new Error(`Variable definition not found for ${type} "${name}"`);
    }

    return definition;
}

/**
 * Gets the display title for a variable or secret field
 * @param {string} name - Parameter name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {string} Display title for the field
 */
function getVariableTitle(name: string, type: CredentialType): string {
    const definition = getVariableDefinition(name, type);
    return definition.label || name;
}

/**
 * Gets the description for a variable or secret field
 * @param {string} name - Parameter name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {string | undefined} Field description or undefined if not available
 */
function getVariableDescription(name: string, type: CredentialType): string | undefined {
    const definition = getVariableDefinition(name, type);
    return definition.description;
}

/**
 * Checks if a variable or secret is optional
 * @param {string} name - Parameter name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {boolean} True if the parameter is optional
 */
function isVariableOptional(name: string, type: CredentialType): boolean {
    const definition = getVariableDefinition(name, type);
    return definition.optional;
}

/**
 * Gets the validation state for a field based on its value and requirements
 * @param {string | null | undefined} value - Current field value
 * @param {string} name - Parameter name
 * @param {CredentialType} type - Type of credential (variable or secret)
 * @returns {boolean | null} Validation state - true if valid, false if invalid, null if neutral
 */
function getFieldState(value: string | null | undefined, name: string, type: CredentialType): boolean | null {
    if (!value) {
        return isVariableOptional(name, type) ? null : false;
    }
    return true;
}
</script>

<template>
    <div class="p-2">
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
