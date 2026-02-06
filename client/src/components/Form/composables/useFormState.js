import { computed, ref } from "vue";

import { matchInputs, validateInputs, visitAllInputs, visitInputs } from "../utilities";

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
        visitAllInputs(formInputs.value, (input) => {
            input.error = null;
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

    function buildFormData() {
        const params = {};
        Object.entries(formIndex.value).forEach(([key, input]) => {
            params[key] = input.value;
        });
        formData.value = params;
        return params;
    }

    function syncServerAttributes(newInputs) {
        const newAttributes = {};
        visitAllInputs(newInputs, (input, name) => {
            newAttributes[name] = input;
        });
        visitAllInputs(formInputs.value, (input, name) => {
            const newValue = newAttributes[name];
            if (newValue != undefined) {
                input.attributes = newValue;
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
            input.error = message;
        }
    }

    function setWarning(inputId, message) {
        const input = formIndex.value[inputId];
        if (input) {
            input.warning = message;
        }
    }

    function resetErrors() {
        Object.values(formIndex.value).forEach((input) => {
            input.error = null;
        });
    }

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
