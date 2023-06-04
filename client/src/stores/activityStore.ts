/**
 * Stores the Activity Bar state
 */

import { defineStore } from "pinia";
import Vue from "vue";

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

export const useActivityStore = defineStore("activityStore", {
    state: () => ({
        activities: [] as Array<Activity>,
    }),
    getters: {
        getAll: (state: any) => {
            return state.activities;
        },
    },
    actions: {
        saveAll(newActivities: Array<Activity>) {
            this.activities = newActivities;
        },
    },
});
