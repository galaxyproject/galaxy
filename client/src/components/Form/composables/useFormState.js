import { computed, ref, set } from "vue";

import { matchInputs, validateInputs, visitAllInputs, visitInputs } from "../utilities";

// Fields owned by the client (clone), never copied from server response into attributes.
const CLIENT_OWNED_FIELDS = new Set(["value", "error", "warning"]);

/**
 * Composable for form state management.
 * Handles cloning, indexing, attribute sync, errors, warnings, and validation.
 * Contains no DOM references or side effects.
 */
export function useFormState(options = {}) {
    const { allowEmptyValueOnRequiredInput = ref(false) } = options;

    const formInputs = ref([]);
    const formIndex = ref({});
    const formData = ref({});

    const validation = computed(() => {
        return validateInputs(formIndex.value, formData.value, allowEmptyValueOnRequiredInput.value);
    });

    function cloneInputs(inputs) {
        formInputs.value = JSON.parse(JSON.stringify(inputs));
        // set() required here: error and warning are genuinely new properties
        // on freshly cloned plain objects that Vue 2.7 hasn't observed yet.
        visitAllInputs(formInputs.value, (input) => {
            set(input, "error", null);
            set(input, "warning", null);
        });
        rebuildIndex();
    }

    function rebuildIndex() {
        const index = {};
        visitInputs(formInputs.value, (input, name) => {
            index[name] = input;
        });
        formIndex.value = index;
    }

    /**
     * Pure computation — builds a flat {paramName: value} dict from the active
     * params in formIndex. Does NOT mutate formData; the caller is responsible
     * for assigning formData.value when appropriate.
     */
    function buildFormData() {
        const params = {};
        Object.entries(formIndex.value).forEach(([key, input]) => {
            params[key] = input.value;
        });
        return params;
    }

    /**
     * Patches input.attributes on clone nodes from the server response.
     * Only copies server-owned fields; value, error, and warning are excluded
     * to maintain the separation between server state (attributes) and client
     * state (the clone's own properties).
     */
    function syncServerAttributes(newInputs) {
        const newAttributes = {};
        visitAllInputs(newInputs, (input, name) => {
            newAttributes[name] = input;
        });
        visitAllInputs(formInputs.value, (input, name) => {
            const serverNode = newAttributes[name];
            if (serverNode != undefined) {
                const attrs = {};
                for (const key in serverNode) {
                    if (!CLIENT_OWNED_FIELDS.has(key)) {
                        attrs[key] = serverNode[key];
                    }
                }
                // set() required: attributes is a genuinely new property on clone nodes.
                set(input, "attributes", attrs);
            }
        });
    }

    function applyErrors(errors) {
        resetErrors();
        if (errors) {
            const errorMessages = matchInputs(formIndex.value, errors);
            for (const inputId in errorMessages) {
                setError(inputId, errorMessages[inputId]);
            }
        }
    }

    function applyWarnings(warnings) {
        if (warnings) {
            const warningMessages = matchInputs(formIndex.value, warnings);
            for (const inputId in warningMessages) {
                setWarning(inputId, warningMessages[inputId]);
            }
        }
    }

    function setError(inputId, message) {
        const input = formIndex.value[inputId];
        if (input) {
            // Plain assignment: error property exists from cloneInputs initialization.
            input.error = message;
        }
    }

    function setWarning(inputId, message) {
        const input = formIndex.value[inputId];
        if (input) {
            // Plain assignment: warning property exists from cloneInputs initialization.
            input.warning = message;
        }
    }

    function resetErrors() {
        Object.values(formIndex.value).forEach((input) => {
            // Plain assignment: error property exists from cloneInputs initialization.
            input.error = null;
        });
    }

    /**
     * Known debt: replaceParams and client-side default selection (FormSelect,
     * FormData auto-selecting first option) are indistinguishable from user edits.
     * Both flow through v-model → onChange → formData. The system has no concept
     * of "inferred default" vs "user intent". This is existing behavior inherited
     * from the Options API implementation, not introduced by this refactor.
     */
    function replaceParams(params) {
        let refreshOnChange = false;
        Object.entries(params).forEach(([key, value]) => {
            const input = formIndex.value[key];
            if (input) {
                input.value = value;
                refreshOnChange = refreshOnChange || input.refresh_on_change;
            }
        });
        return refreshOnChange;
    }

    return {
        formInputs,
        formIndex,
        formData,
        validation,
        cloneInputs,
        rebuildIndex,
        buildFormData,
        syncServerAttributes,
        applyErrors,
        applyWarnings,
        setError,
        setWarning,
        resetErrors,
        replaceParams,
    };
}
