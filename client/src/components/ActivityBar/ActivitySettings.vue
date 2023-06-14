<script setup lang="ts">
import { computed, ref, type Ref, type ComputedRef } from "vue";
import { storeToRefs } from "pinia";
import { useActivityStore, type Activity } from "@/stores/activityStore";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faCheckSquare, faTrash, faThumbtack } from "@fortawesome/free-solid-svg-icons";
import DelayedInput from "@/components/Common/DelayedInput.vue";

library.add({
    faCheckSquare,
    faSquare,
    faTrash,
    faThumbtack,
});

const activityStore = useActivityStore();
const { activities } = storeToRefs(activityStore);
const query: Ref<string> = ref("");

const filteredActivities = computed(() => {
    if (query.value.length > 0) {
        const queryLower = query.value.toLowerCase();
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

function onClick(activity: Activity) {
    if (activity.optional) {
        activity.visible = !activity.visible;
    }
}

function onRemove(activity: Activity) {
    activityStore.remove(activity.id);
}

function onQuery(newQuery: string) {
    query.value = newQuery;
}
</script>

<template>
    <div class="activity-settings rounded p-3 no-highlight">
        <delayed-input class="mb-3" :delay="100" placeholder="Search activities" @change="onQuery" />
        <div v-if="foundActivities" class="activity-settings-content overflow-auto">
            <div v-for="activity in filteredActivities" :key="activity.id">
                <div class="activity-settings-item p-2 cursor-pointer" @click="onClick(activity)">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="w-100">
                            <font-awesome-icon
                                v-if="!activity.optional"
                                class="icon-check mr-1"
                                icon="fas fa-thumbtack"
                                fa-fw />
                            <font-awesome-icon
                                v-else-if="activity.visible"
                                class="icon-check mr-1"
                                icon="fas fa-check-square"
                                fa-fw />
                            <font-awesome-icon v-else class="mr-1" icon="far fa-square" fa-fw />
                            <small>
                                <icon class="mr-1" :icon="activity.icon" />
                                <span v-localize class="font-weight-bold">{{
                                    activity.title || "No title available"
                                }}</span>
                            </small>
                        </span>
                        <b-button
                            v-if="activity.mutable"
                            data-description="delete activity"
                            class="button-delete"
                            size="sm"
                            variant="link"
                            @click.stop="onRemove(activity)">
                            <font-awesome-icon icon="fa-trash" fa-fw />
                        </b-button>
                    </div>
                    <small v-localize>
                        {{ activity.description || "No description available" }}
                    </small>
                </div>
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
    width: 20rem;
}

.activity-settings-content {
    height: 20rem;
}

.activity-settings-item {
    .icon-check {
        color: darken($brand-success, 15%);
    }
    .button-delete {
        background: transparent;
    }
}
.activity-settings-item:hover {
    background: $brand-primary;
    color: $brand-light;
    border-radius: $border-radius-large;
    .icon-check {
        color: $brand-light;
    }
    .button-delete {
        color: $brand-light;
    }
}
</style>
