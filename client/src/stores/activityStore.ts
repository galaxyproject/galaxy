/**
 * Stores the Activity Bar state
 */

import { ref, type Ref } from "vue";
import { defineStore } from "pinia";

import { Activities } from "./activitySetup";

export interface Activity {
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
        const activities: Ref<Array<Activity>> = ref([]);

        /**
         * The set of built-in activities is defined in activitySetup.js.
         * This helper function applies changes of the built-in activities,
         * to the user stored activities which are persisted in local cache.
         */
        function sync() {
            // create a map of built-in activities
            const activitiesMap: Record<string, Activity> = {};
            Activities.forEach((a) => {
                activitiesMap[a.id] = a;
            });
            // create an updated array of activities
            const newActivities: Array<Activity> = [];
            const foundActivity = new Set();
            activities.value.forEach((a: Activity) => {
                if (a.mutable) {
                    // existing custom activity
                    newActivities.push({ ...a });
                } else {
                    // update existing built-in activity attributes
                    // skip legacy built-in activities
                    const sourceActivity = activitiesMap[a.id];
                    if (sourceActivity) {
                        foundActivity.add(a.id);
                        newActivities.push({
                            ...sourceActivity,
                            visible: a.visible,
                        });
                    }
                }
            });
            // add new built-in activities
            Activities.forEach((a) => {
                if (!foundActivity.has(a.id)) {
                    newActivities.push({ ...a });
                }
            });
            // update activities stored in local cache only if changes were applied
            if (JSON.stringify(activities.value) !== JSON.stringify(newActivities)) {
                activities.value = newActivities;
            }
        }

        function getAll() {
            return activities.value;
        }

        function setAll(newActivities: Array<Activity>) {
            activities.value = newActivities;
        }

        function remove(activityId: string) {
            const findIndex = activities.value.findIndex((a: Activity) => a.id === activityId);
            if (findIndex !== -1) {
                activities.value.splice(findIndex, 1);
            }
        }

        return {
            activities,
            getAll,
            remove,
            setAll,
            sync,
        };
    },
    {
        persist: {
            paths: ["activities"],
        },
    }
);
