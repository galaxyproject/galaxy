import type { ComputedRef, Ref } from "vue";
import { computed, ref, set } from "vue";

import type { FormParameterValue } from "../parameterTypes";
import { matchInputs, validateInputs, visitAllInputs, visitInputs } from "../utilities";

/** A single input node in the nested form tree (leaf, conditional, repeat, or section). */
export interface FormInputNode {
    name: string;
    type: string;
    value?: FormParameterValue;
    error?: string | null;
    warning?: string | null;
    attributes?: Record<string, unknown>;
    options?: unknown[];
    label?: string;
    help?: string | null;
    help_format?: string;
    optional?: boolean;
    refresh_on_change?: boolean;
    hidden?: boolean;
    wp_linked?: boolean;
    step_linked?: boolean;
    text_value?: string;
    validators?: Array<Record<string, unknown>>;
    connectable?: boolean;
    // Container types
    test_param?: FormInputNode;
    cases?: Array<{ value: string; inputs: FormInputNode[] }>;
    cache?: FormInputNode[][];
    inputs?: FormInputNode[];
    expanded?: boolean;
}

/** Flat dictionary mapping paramName → value, ready for submission. */
export type FormData = Record<string, FormParameterValue>;

/** Flat dictionary mapping paramName → input node, for active params only. */
export type FormIndex = Record<string, FormInputNode>;

/** Nested error/warning structure from server validation response. */
export type FormMessages = Record<string, unknown>;

/** Options for the useFormState composable. */
export interface UseFormStateOptions {
    rejectEmptyRequiredInputs?: Ref<boolean>;
}

/** Return type of the useFormState composable. */
export interface UseFormStateReturn {
    formInputs: Ref<FormInputNode[]>;
    formIndex: Ref<FormIndex>;
    formData: Ref<FormData>;
    validation: ComputedRef<[string, string] | null>;
    cloneInputs: (inputs: FormInputNode[]) => void;
    rebuildIndex: () => void;
    buildFormData: () => FormData;
    syncServerAttributes: (newInputs: FormInputNode[]) => void;
    applyErrors: (errors: FormMessages | null) => void;
    applyWarnings: (warnings: FormMessages | null) => void;
    setError: (inputId: string, message: string) => void;
    setWarning: (inputId: string, message: string) => void;
    resetErrors: () => void;
    replaceParams: (params: Record<string, FormParameterValue>) => boolean;
}

// Fields owned by the client (clone), never copied from server response into attributes.
const CLIENT_OWNED_FIELDS = new Set(["value", "error", "warning"]);

/**
 * Composable for form state management.
 * Handles cloning, indexing, attribute sync, errors, warnings, and validation.
 * Contains no DOM references or side effects.
 */
export function useFormState(options: UseFormStateOptions = {}): UseFormStateReturn {
    const { rejectEmptyRequiredInputs = ref(false) } = options;

    const formInputs = ref<FormInputNode[]>([]);
    const formIndex = ref<FormIndex>({});
    const formData = ref<FormData>({});

    const validation = computed<[string, string] | null>(() => {
        return validateInputs(formIndex.value, formData.value, rejectEmptyRequiredInputs.value) as
            | [string, string]
            | null;
    });

    function cloneInputs(inputs: FormInputNode[]): void {
        formInputs.value = JSON.parse(JSON.stringify(inputs));
        // set() required here: error and warning are genuinely new properties
        // on freshly cloned plain objects that Vue 2.7 hasn't observed yet.
        visitAllInputs(formInputs.value, (input: FormInputNode) => {
            set(input, "error", null);
            set(input, "warning", null);
        });
        rebuildIndex();
    }

    function rebuildIndex(): void {
        const index: FormIndex = {};
        visitInputs(formInputs.value, (input: FormInputNode, name: string) => {
            index[name] = input;
        });
        formIndex.value = index;
    }

    /**
     * Pure computation — builds a flat {paramName: value} dict from the active
     * params in formIndex. Does NOT mutate formData; the caller is responsible
     * for assigning formData.value when appropriate.
     */
    function buildFormData(): FormData {
        const params: FormData = {};
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
    function syncServerAttributes(newInputs: FormInputNode[]): void {
        const newAttributes: Record<string, FormInputNode> = {};
        visitAllInputs(newInputs, (input: FormInputNode, name: string) => {
            newAttributes[name] = input;
        });
        visitAllInputs(formInputs.value, (input: FormInputNode, name: string) => {
            const serverNode = newAttributes[name];
            if (serverNode != undefined) {
                const attrs: Record<string, unknown> = {};
                const raw = serverNode as unknown as Record<string, unknown>;
                for (const key in raw) {
                    if (!CLIENT_OWNED_FIELDS.has(key)) {
                        attrs[key] = raw[key];
                    }
                }
                // set() required: attributes is a genuinely new property on clone nodes.
                set(input, "attributes", attrs);
            }
        });
    }

    function applyErrors(errors: FormMessages | null): void {
        resetErrors();
        if (errors) {
            const errorMessages = matchInputs(formIndex.value, errors) as Record<string, string>;
            for (const inputId in errorMessages) {
                setError(inputId, errorMessages[inputId]!);
            }
        }
    }

    function applyWarnings(warnings: FormMessages | null): void {
        if (warnings) {
            const warningMessages = matchInputs(formIndex.value, warnings) as Record<string, string>;
            for (const inputId in warningMessages) {
                setWarning(inputId, warningMessages[inputId]!);
            }
        }
    }

    function setError(inputId: string, message: string): void {
        const input = formIndex.value[inputId];
        if (input) {
            // Plain assignment: error property exists from cloneInputs initialization.
            input.error = message;
        }
    }

    function setWarning(inputId: string, message: string): void {
        const input = formIndex.value[inputId];
        if (input) {
            // Plain assignment: warning property exists from cloneInputs initialization.
            input.warning = message;
        }
    }

    function resetErrors(): void {
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
    function replaceParams(params: Record<string, FormParameterValue>): boolean {
        let refreshOnChange = false;
        Object.entries(params).forEach(([key, value]) => {
            const input = formIndex.value[key];
            if (input) {
                input.value = value;
                refreshOnChange = refreshOnChange || !!input.refresh_on_change;
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
