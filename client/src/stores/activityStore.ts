/**
 * Stores the Activity Bar state
 */

import { ref, type Ref } from "vue";
import { defineStore } from "pinia";

import Activities from "@/components/ActivityBar/activities";

interface Activity {
    id: string;
    title: string;
    description: string;
    icon: string;
    tooltip: string;
    to: string;
    optional: boolean;
    mutable: boolean;
}

export const useActivityStore = defineStore(
    "activityStore",
    () => {
        const activities: Ref<Array<Activity>> = ref([]);

        function getAll() {
            return activities.value;
        }

        function saveAll(newActivities: Array<Activity>) {
            activities.value = newActivities;
        }

        return {
            getAll,
            saveAll,
        };
    },
    {
        persist: {
            paths: ["activities"],
        },
    }
);
