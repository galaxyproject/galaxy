import { computed, type Ref, ref, watch } from "vue";

import { escapeRegExp } from "@/utils/regExp";

import { useConfig } from "./config";

type TrainingDetails = {
    tool_id: Array<
        [
            string, // toolshed tool ID
            string // Version
        ]
    >;
    tutorials: Array<
        [
            string, // tutorial ID (unused)
            string, // Title
            string, // Category
            string // URL
        ]
    >;
};

type TrainingMaterialResponse = {
    [id: string]: TrainingDetails;
};

export type TutorialDetails = {
    category: string;
    title: string;
    url: URL;
};

/** caches the response of the training material api */
const cachedResponse: Ref<TrainingMaterialResponse | null> = ref(null);

/** maps toolshed tool ids to training tool ids */
const toolIdMap: Map<string, string> = new Map();

function mapToolIds() {
    Object.entries(cachedResponse.value ?? {}).forEach(([trainingId, details]) => {
        details.tool_id.forEach(([id, version]) => {
            if (id === version) {
                // built-in tool
                toolIdMap.set(id, trainingId);
            } else {
                const regEx = new RegExp(`${escapeRegExp(version)}$`);
                const trimmedId = id.replace(regEx, "");

                toolIdMap.set(trimmedId, trainingId);
            }
        });
    });
}

/** Training information about given tool */
export function useToolTrainingMaterial(id: string, name: string, version: string, owner?: string) {
    const { config, isConfigLoaded } = useConfig();
    const apiEnabled = computed(() => {
        return Boolean(
            isConfigLoaded.value &&
                config.value.tool_training_recommendations &&
                config.value.tool_training_recommendations_api_url
        );
    });

    const cacheLoaded = ref(false);

    watch(
        () => isConfigLoaded.value,
        async () => {
            if (!isConfigLoaded.value) {
                return;
            }

            if (apiEnabled.value && !cachedResponse.value) {
                const res = await fetch(config.value.tool_training_recommendations_api_url);

                if (res.ok) {
                    cachedResponse.value = await res.json();
                    mapToolIds();
                }
            }

            cacheLoaded.value = true;
        },
        { immediate: true }
    );

    const identifier = computed(() => {
        const regEx = new RegExp(`${escapeRegExp(version)}$`);
        const trimmedId = id.replace(regEx, "");

        if (!cacheLoaded.value) {
            return trimmedId;
        } else {
            return toolIdMap.get(trimmedId) ?? trimmedId;
        }
    });

    const trainingAvailable = computed(() => {
        if (!apiEnabled.value || !cachedResponse.value) {
            return false;
        }

        return Object.keys(cachedResponse.value).includes(identifier.value);
    });

    const trainingDetails = computed(() => {
        if (!trainingAvailable.value) {
            return null;
        }

        return cachedResponse.value?.[identifier.value] ?? null;
    });

    const trainingCategories = computed<string[]>(() => {
        if (!trainingDetails.value) {
            return [];
        }

        const categories = new Set<string>();

        trainingDetails.value.tutorials.forEach((tutorial) => {
            categories.add(tutorial[2]);
        });

        return Array.from(categories);
    });

    const tutorialDetails = computed<TutorialDetails[]>(() => {
        if (!trainingDetails.value) {
            return [];
        }

        const details: TutorialDetails[] = [];

        trainingDetails.value.tutorials.forEach((tutorial) => {
            details.push({
                title: tutorial[1],
                category: tutorial[2],
                url: new URL(tutorial[3], config.value.tool_training_recommendations_api_url),
            });
        });

        return details;
    });

    const allTutorialsUrl = computed<string | undefined>(() => {
        if (!cacheLoaded.value || !config.value.tool_training_recommendations_link) {
            return;
        }

        let url = config.value.tool_training_recommendations_link;

        url = url.replace("{training_tool_identifier}", identifier.value);
        url = url.replace("{tool_id}", id);
        url = url.replace("{name}", name);
        url = url.replace("{repository_owner}", owner ?? "");
        url = url.replace("{version}", version);

        return url;
    });

    const versionAvailable = computed<boolean>(() => {
        if (!trainingDetails.value) {
            return false;
        }

        for (let i = 0; i < trainingDetails.value.tool_id.length; i++) {
            const element = trainingDetails.value.tool_id[i]!;

            if (element[1] === version) {
                return true;
            }
        }

        return false;
    });

    return {
        trainingAvailable,
        trainingCategories,
        tutorialDetails,
        allTutorialsUrl,
        versionAvailable,
    };
}
