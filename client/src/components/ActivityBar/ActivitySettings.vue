<script setup lang="ts">
import { faStar as faStarRegular } from "@fortawesome/free-regular-svg-icons";
import { faStar, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, type ComputedRef } from "vue";
import { useRouter } from "vue-router/composables";

import { useActivityStore } from "@/stores/activityStore";
import type { Activity } from "@/stores/activityStoreTypes";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

import GButton from "@/components/BaseComponents/GButton.vue";

const props = defineProps<{
    activityBarId: string;
    query: string;
}>();

const emit = defineEmits<{
    (e: "activityClicked", activityId: string): void;
}>();

const activityStore = useActivityStore(props.activityBarId);

const unprivilegedToolStore = useUnprivilegedToolStore();
const { canUseUnprivilegedTools } = storeToRefs(unprivilegedToolStore);

const optionalActivities = computed(() => {
    return activityStore.activities.filter(
        (a) => (a.optional && a.id !== "user-defined-tools") || canUseUnprivilegedTools.value
    );
});

const filteredActivities = computed(() => {
    if (props.query?.length > 0) {
        const queryLower = props.query.toLowerCase();
        const results = optionalActivities.value.filter((a: Activity) => {
            const attributeValues = [a.title, a.description];
            for (const value of attributeValues) {
                if (value.toLowerCase().indexOf(queryLower) !== -1) {
                    return true;
                }
            }
            return false;
        });
        return results;
    } else {
        return optionalActivities.value;
    }
});

const foundActivities: ComputedRef<boolean> = computed(() => {
    return filteredActivities.value.length > 0;
});

function onFavorite(activity: Activity) {
    if (activity.optional) {
        activity.visible = !activity.visible;
    }
}

function onRemove(activity: Activity) {
    activityStore.remove(activity.id);
}

const router = useRouter();

function executeActivity(activity: Activity) {
    if (activity.click) {
        emit("activityClicked", activity.id);
    }

    if (activity.panel) {
        activityStore.toggleSideBar(activity.id);
    }

    if (activity.to) {
        router.push(activity.to);
    }
}
</script>

<template>
    <div>
        <div v-if="foundActivities">
            <button
                v-for="activity in filteredActivities"
                :key="activity.id"
                class="activity-settings-item p-2 cursor-pointer"
                @click="executeActivity(activity)">
                <div class="d-flex justify-content-between align-items-start">
                    <span class="d-flex justify-content-between w-100">
                        <span>
                            <FontAwesomeIcon class="mr-1" :icon="activity.icon" />
                            <span v-localize class="font-weight-bold">{{
                                activity.title || "No title available"
                            }}</span>
                        </span>
                        <div>
                            <GButton
                                v-if="activity.mutable"
                                tooltip
                                data-description="delete activity"
                                size="small"
                                transparent
                                icon-only
                                color="blue"
                                title="Delete Activity"
                                @click.stop="onRemove(activity)">
                                <FontAwesomeIcon :icon="faTrash" fa-fw />
                            </GButton>
                            <GButton
                                v-if="activity.visible"
                                tooltip
                                size="small"
                                transparent
                                icon-only
                                color="blue"
                                title="Hide in Activity Bar"
                                @click.stop="onFavorite(activity)">
                                <FontAwesomeIcon :icon="faStar" fa-fw />
                            </GButton>
                            <GButton
                                v-else
                                tooltip
                                transparent
                                icon-only
                                color="blue"
                                size="small"
                                title="Show in Activity Bar"
                                @click.stop="onFavorite(activity)">
                                <FontAwesomeIcon :icon="faStarRegular" fa-fw />
                            </GButton>
                        </div>
                    </span>
                </div>
                <div v-localize class="text-muted">
                    {{ activity.description || "No description available" }}
                </div>
            </button>
        </div>
        <div v-else>
            <b-alert v-localize class="py-1 px-2" show> No matching activities found. </b-alert>
        </div>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.activity-settings-item {
    background: none;
    border: none;
    text-align: left;
    transition: none;
    width: 100%;
}

.activity-settings-item:hover {
    background: $gray-200;
}
</style>
