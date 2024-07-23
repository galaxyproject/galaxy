import { defineStore, storeToRefs } from "pinia";
import { type Ref, ref, set } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";

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

type PreferenceOptions<T> = {
    id: string;
    default: T;
    category?: Readonly<PreferenceCategoryOptions>;
    name?: string;
    description?: string;
};

type Preference<T> = {
    name: string;
    description?: string;
    default: T;
    ref: Ref<T>;
};

/**
 * Creates a user scoped stored ref, and writes it to the preference tree
 * @param preferenceTree tree of all preferences which this preference will be written to
 * @param options
 * @returns ref to the preference
 */
function useLocalPreference<T>(preferenceTree: Ref<PreferenceTree>, options: Readonly<PreferenceOptions<T>>): Ref<T> {
    const preferencesRef = useUserLocalStorage(`local-preferences-store-${options.id}`, options.default) as Ref<T>;

    const preference: Preference<T> = {
        name: options.name ?? options.id,
        description: options.description,
        default: structuredClone(options.default),
        ref: preferencesRef,
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

    return preferencesRef;
}

export const useLocalPreferencesStore = defineStore("localPreferences", () => {
    const allPreferences = ref({
        uncategorized: [],
        categories: {},
    }) as Ref<PreferenceTree>;

    const preferredFormSelectElement = useLocalPreference<"none" | "multi" | "many">(allPreferences, {
        id: "preferred-form-select",
        default: "none",
        name: "Preferred Form Select Element",
    });

    return {
        allPreferences,
        preferredFormSelectElement,
    };
});

export const useLocalPreferences = storeToRefs(useLocalPreferencesStore());
