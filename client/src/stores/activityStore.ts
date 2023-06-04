/**
 * Stores the Activity Bar state
 */

import { ref, type Ref } from "vue";
import { defineStore } from "pinia";

import Activities from "@/components/ActivityBar/activities";

interface Activity {
    description: string;
    id: string;
    icon: string;
    mutable: boolean;
    optional: boolean;
    title: string;
    to: string | null;
    tooltip: string;
    visible: boolean;
}

export const useActivityStore = defineStore(
    "activityStore",
    () => {
        const activities: Ref<Array<Activity>> = ref(Activities);

        function getAll() {
            return activities.value;
        }

        function saveAll(newActivities: Array<Activity>) {
            activities.value = newActivities;
        }

        return {
            activities,
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
