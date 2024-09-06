/**
 * Stores the Activity Bar state
 */

import { defineStore } from "pinia";
import { type Ref } from "vue";

import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useConfig } from "@/composables/config";

import { getActivities } from "./activitySetup";

export interface Activity {
    // determine wether an anonymous user can access this activity
    anonymous: boolean;
    // description of the activity
    description: string;
    // unique identifier
    id: string;
    // icon to be displayed in activity bar
    icon: string;
    // indicate if this activity can be modified and/or deleted
    mutable: boolean;
    // indicate wether this activity can be disabled by the user
    optional: boolean;
    // specifiy wether this activity utilizes the side panel
    panel: boolean;
    // title to be displayed in the activity bar
    title: string;
    // route to be executed upon selecting the activity
    to: string | null;
    // tooltip to be displayed when hovering above the icon
    tooltip: string;
    // indicate wether the activity should be visible by default
    visible: boolean;
}

export type ClientMode = "full" | "workflow_centric" | "workflow_runner";

// config materializes a RawActivity into an Activity
export interface RawActivity {
    // determine wether an anonymous user can access this activity
    anonymous: boolean;
    // description of the activity
    description: string;
    // unique identifier
    id: string;
    // icon to be displayed in activity bar
    icon: string;
    // indicate if this activity can be modified and/or deleted
    mutable: boolean;
    // indicate wether this activity can be disabled by the user
    optional: boolean | ((mode: ClientMode) => boolean);
    // specifiy wether this activity utilizes the side panel
    panel: boolean;
    // title to be displayed in the activity bar
    title: string;
    // route to be executed upon selecting the activity
    to: string | null;
    // tooltip to be displayed when hovering above the icon
    tooltip: string;
    // indicate wether the activity should be visible by default
    visible: boolean | ((mode: ClientMode) => boolean);
}

export const useActivityStore = defineStore("activityStore", () => {
    const activities: Ref<Array<Activity>> = useUserLocalStorage("activity-store-activities", []);

    /**
     * Restores the default activity bar items
     */
    function restore() {
        activities.value = Activities.slice();
    }

    /**
     * The set of built-in activities is defined in activitySetup.js.
     * This helper function applies changes of the built-in activities,
     * to the user stored activities which are persisted in local cache.
     */
    function sync() {
        const { config, isConfigLoaded } = useConfig();
        if (!isConfigLoaded.value) {
            return;
        }

        // create a map of built-in activities
        const activitiesMap: Record<string, Activity> = {};
        let activityDefs = getActivities(config.value.client_mode);
        activityDefs.forEach((a) => {
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
        activityDefs.forEach((a) => {
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
        restore,
        sync,
    };
});
