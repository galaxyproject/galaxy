/**
 * Stores the Activity Bar state
 */
import { useDebounceFn, watchImmediate } from "@vueuse/core";
import { computed, type Ref, ref } from "vue";

import { useHashedUserId } from "@/composables/hashedUserId";
import { useUserLocalStorage } from "@/composables/userLocalStorage";

import { defaultActivities } from "./activitySetup";
import { defineScopedStore } from "./scopedStore";

export interface Activity {
    // determine wether an anonymous user can access this activity
    anonymous?: boolean;
    // description of the activity
    description: string;
    // unique identifier
    id: string;
    // icon to be displayed in activity bar
    icon: string | object;
    // indicate if this activity can be modified and/or deleted
    mutable?: boolean;
    // indicate wether this activity can be disabled by the user
    optional?: boolean;
    // specifiy wether this activity utilizes the side panel
    panel?: boolean;
    // title to be displayed in the activity bar
    title: string;
    // route to be executed upon selecting the activity
    to?: string | null;
    // tooltip to be displayed when hovering above the icon
    tooltip: string;
    // indicate wether the activity should be visible by default
    visible?: boolean;
    // if activity should cause a click event
    click?: true;
}

export const useActivityStore = defineScopedStore("activityStore", (scope) => {
    const activities: Ref<Array<Activity>> = useUserLocalStorage(`activity-store-activities-${scope}`, []);

    const { hashedUserId } = useHashedUserId();

    const customDefaultActivities = ref<Activity[] | null>(null);
    const currentDefaultActivities = computed(() => customDefaultActivities.value ?? defaultActivities);

    const toggledSideBar = useUserLocalStorage(`activity-store-current-side-bar-${scope}`, "tools");

    function toggleSideBar(currentOpen = "") {
        toggledSideBar.value = toggledSideBar.value === currentOpen ? "" : currentOpen;
    }

    function overrideDefaultActivities(activities: Activity[]) {
        customDefaultActivities.value = activities;
        sync();
    }

    function resetDefaultActivities() {
        customDefaultActivities.value = null;
        sync();
    }

    /**
     * Restores the default activity bar items
     */
    function restore() {
        activities.value = currentDefaultActivities.value.slice();
    }

    /**
     * The set of built-in activities is defined in activitySetup.js.
     * This helper function applies changes of the built-in activities,
     * to the user stored activities which are persisted in local cache.
     */
    const sync = useDebounceFn(() => {
        // create a map of built-in activities
        const activitiesMap: Record<string, Activity> = {};

        currentDefaultActivities.value.forEach((a) => {
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
        currentDefaultActivities.value.forEach((a) => {
            if (!foundActivity.has(a.id)) {
                newActivities.push({ ...a });
            }
        });

        // update activities stored in local cache only if changes were applied
        if (JSON.stringify(activities.value) !== JSON.stringify(newActivities)) {
            activities.value = newActivities;
        }

        // if toggled side-bar does not exist, choose the first option
        if (toggledSideBar.value !== "") {
            const allSideBars = activities.value.flatMap((activity) => {
                if (activity.panel) {
                    return [activity.id];
                } else {
                    return [];
                }
            });

            const allSideBarsSet = new Set(allSideBars);
            const firstSideBar = allSideBars[0];

            if (firstSideBar && !allSideBarsSet.has(toggledSideBar.value)) {
                toggledSideBar.value = firstSideBar;
            }
        }
    }, 10);

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

    watchImmediate(
        () => hashedUserId.value,
        () => {
            sync();
        }
    );

    return {
        toggledSideBar,
        toggleSideBar,
        activities,
        getAll,
        remove,
        setAll,
        restore,
        sync,
        customDefaultActivities,
        currentDefaultActivities,
        overrideDefaultActivities,
        resetDefaultActivities,
    };
});
