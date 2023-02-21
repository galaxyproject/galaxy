import { useConfig } from "./config";
import { computed, ref, watch, type Ref } from "vue";

type Name = string;
type Repo = string;
type ID = string;

type TrainingId = `${Repo}/${Name}` | ID;

type TrainingDetails = {
    tool_id: Array<
        [
            string, // ID (unused)
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
    [id: TrainingId]: TrainingDetails;
};

type Config = {
    tool_training_recommendations: boolean;
    tool_training_recommendations_api_url: string;
    tool_training_recommendations_link: string;
};

export type TutorialDetails = {
    category: string;
    title: string;
    url: URL;
};

const cachedResponse: Ref<TrainingMaterialResponse | null> = ref(null);

export function useToolTrainingMaterial(id: ID, name: Name, version: string, repo?: Repo) {
    const { config, isLoaded }: { config: Ref<Config>; isLoaded: Ref<boolean> } = useConfig();
    const apiEnabled = computed(() => {
        return Boolean(
            isLoaded.value &&
                config.value.tool_training_recommendations &&
                config.value.tool_training_recommendations_api_url
        );
    });

    watch(
        () => isLoaded.value,
        async () => {
            if (!isLoaded.value) {
                return;
            }

            if (apiEnabled.value && !cachedResponse.value) {
                const res = await fetch(config.value.tool_training_recommendations_api_url);

                if (res.ok) {
                    cachedResponse.value = await res.json();
                }
            }
        },
        { immediate: true }
    );

    const identifier = computed(() => {
        if (repo) {
            return `${repo}/${name.toLowerCase()}`;
        } else {
            return id;
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
        if (!isLoaded.value || !config.value.tool_training_recommendations_link) {
            return;
        }

        let url = config.value.tool_training_recommendations_link;

        url = url.replace("{training_tool_identifier}", identifier.value);
        url = url.replace("{tool_id}", id);
        url = url.replace("{name}", name);
        url = url.replace("{repository}", repo ?? "");
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
