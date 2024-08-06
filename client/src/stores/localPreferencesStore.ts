import { defineStore, storeToRefs } from "pinia";
import { computed, type Ref, ref, set } from "vue";

import { useClamp, useStep } from "@/composables/math";
import { useInSet } from "@/composables/string";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { ensureDefined } from "@/utils/assertions";

type PreferenceTree = {
    uncategorized: Preference<unknown>[];
    categories: {
        [id: string]: PreferenceCategory;
    };
};

type PreferenceCategoryOptions = {
    id: string;
    name: string;
    description?: string;
};

type PreferenceCategory = {
    preferences: Preference<unknown>[];
} & PreferenceCategoryOptions;

type SelectOption = {
    label: string;
    value: string;
};

type PreferenceTypeOption = {
    option: true;
    options: SelectOption[];
};

type PreferenceTypeBoolean = {
    boolean: true;
};

type PreferenceTypeNumber = {
    number: true;
    range?: {
        min: number;
        max: number;
    };
    step?: number;
};

type PreferenceType = PreferenceTypeOption | PreferenceTypeBoolean | PreferenceTypeNumber;

type PreferenceOptions<T> = {
    id: string;
    default: T;
    type: PreferenceType;
    category?: Readonly<PreferenceCategoryOptions>;
    name?: string;
    description?: string;
};

export type Preference<T> = {
    id: string;
    name: string;
    description?: string;
    default: T;
    type: PreferenceType;
};

/**
 * wraps type constraints around refs
 */
function useTypeConstrainedRef<T>(ref: Ref<T>, type: PreferenceType): Ref<T> {
    if ("option" in type) {
        return useInSet(
            ref as Ref<string>,
            type.options.map((o) => o.value)
        ) as Ref<T>;
    }

    if ("number" in type) {
        let constrainedRef = ref as Ref<number>;

        if (type.step) {
            constrainedRef = useStep(constrainedRef, type.step);
        }

        if (type.range) {
            constrainedRef = useClamp(constrainedRef, type.range.min, type.range.max);
        }

        return constrainedRef as Ref<T>;
    }

    return ref;
}

/**
 * Creates a user scoped stored ref, and writes it to the preference tree
 * @param preferenceTree tree of all preferences which this preference will be written to
 * @param options
 * @returns ref to the preference
 */
function useLocalPreference<T>(
    preferenceTree: Ref<PreferenceTree>,
    refsById: Record<string, Ref<unknown>>,
    options: Readonly<PreferenceOptions<T>>
): Ref<T> {
    const preferencesRef = useUserLocalStorage(`local-preferences-store-${options.id}`, options.default) as Ref<T>;

    const preference: Preference<T> = {
        id: options.id,
        name: options.name ?? options.id,
        description: options.description,
        default: structuredClone(options.default),
        type: structuredClone(options.type),
    };

    if (options.category) {
        const category =
            preferenceTree.value.categories[options.category.id] ??
            (() => {
                const newCategory: PreferenceCategory = {
                    ...options.category,
                    preferences: [],
                };

                set(preferenceTree.value.categories, options.category.id, newCategory);

                return newCategory;
            })();

        category.preferences.push(preference);
    } else {
        preferenceTree.value.uncategorized.push(preference);
    }

    const constrainedRef = useTypeConstrainedRef(preferencesRef, options.type);

    refsById[options.id] = constrainedRef;

    return constrainedRef;
}

export const useLocalPreferencesStore = defineStore("localPreferencesStore", () => {
    const allPreferences = ref({
        uncategorized: [],
        categories: {},
    }) as Ref<PreferenceTree>;

    const preferenceRefsById: Record<string, Ref<unknown>> = {};

    const preferredFormSelectElement = useLocalPreference<"none" | "multi" | "many">(
        allPreferences,
        preferenceRefsById,
        {
            id: "preferred-form-select",
            default: "none",
            name: "Preferred Form Multi-Select Element",
            description: "The preferred type of multi-select element to appear in forms by default.",
            type: {
                option: true,
                options: [
                    { label: "No preference", value: "none" },
                    { label: "Multi-Select (dropdown)", value: "multi" },
                    { label: "Column-Select", value: "many" },
                ],
            },
        }
    );

    const getValueForId = computed(() => (id: string) => ensureDefined(preferenceRefsById[id]).value);

    function setValueForId(id: string, value: unknown) {
        ensureDefined(preferenceRefsById[id]).value = value;
    }

    return {
        allPreferences,
        preferredFormSelectElement,
        getValueForId,
        setValueForId,
    };
});

export function useLocalPreferences() {
    return storeToRefs(useLocalPreferencesStore());
}
