<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSquare, faStar as faStarRegular } from "@fortawesome/free-regular-svg-icons";
import { faCheckSquare, faStar, faThumbtack, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, type ComputedRef } from "vue";

import { useActivityAction } from "@/composables/useActivityAction";
import { type Activity, useActivityStore } from "@/stores/activityStore";

library.add({
    faCheckSquare,
    faSquare,
    faStar,
    faStarRegular,
    faTrash,
    faThumbtack,
});

const props = defineProps<{
    activityBarScope: string;
    query: string;
}>();

const activityStore = useActivityStore(props.activityBarScope);
const { activities } = storeToRefs(activityStore);
const activityAction = useActivityAction();

const filteredActivities = computed(() => {
    if (props.query?.length > 0) {
        const queryLower = props.query.toLowerCase();
        const results = activities.value.filter((a: Activity) => {
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
        return activities.value;
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
</script>

<template>
    <div class="activity-settings rounded no-highlight">
        <div v-if="foundActivities" class="activity-settings-content">
            <div v-for="activity in filteredActivities" :key="activity.id">
                <button
                    v-if="activity.optional"
                    class="activity-settings-item p-2 cursor-pointer"
                    @click="activityAction.executeActivity(activity)">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="d-flex justify-content-between w-100">
                            <span>
                                <icon class="mr-1" :icon="activity.icon" />
                                <span v-localize class="font-weight-bold">{{
                                    activity.title || "No title available"
                                }}</span>
                            </span>
                            <div>
                                <BButton
                                    v-if="activity.mutable"
                                    v-b-tooltip.hover
                                    data-description="delete activity"
                                    size="sm"
                                    title="Delete Activity"
                                    variant="link"
                                    @click.stop="onRemove(activity)">
                                    <FontAwesomeIcon icon="fa-trash" fa-fw />
                                </BButton>
                                <BButton
                                    v-if="activity.visible"
                                    v-b-tooltip.hover
                                    size="sm"
                                    title="Hide in Activity Bar"
                                    variant="link"
                                    @click.stop="onFavorite(activity)">
                                    <FontAwesomeIcon icon="fas fa-star" fa-fw />
                                </BButton>
                                <BButton
                                    v-else
                                    v-b-tooltip.hover
                                    size="sm"
                                    title="Show in Activity Bar"
                                    variant="link"
                                    @click.stop="onFavorite(activity)">
                                    <FontAwesomeIcon icon="far fa-star" fa-fw />
                                </BButton>
                            </div>
                        </span>
                    </div>
                    <div v-localize class="text-muted">
                        {{ activity.description || "No description available" }}
                    </div>
                </button>
            </div>
        </div>
        <div v-else class="activity-settings-content">
            <b-alert v-localize class="py-1 px-2" show> No matching activities found. </b-alert>
        </div>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.activity-settings {
    overflow-y: hidden;
    display: flex;
    flex-direction: column;
}

.activity-settings-content {
    overflow-y: auto;
}

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
