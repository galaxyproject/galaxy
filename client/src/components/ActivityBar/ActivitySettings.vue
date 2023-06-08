<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useActivityStore, type Activity } from "@/stores/activityStore";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faCheckSquare, faTrash } from "@fortawesome/free-solid-svg-icons";

library.add({
    faCheckSquare,
    faSquare,
    faTrash,
});

const activityStore = useActivityStore();
const { activities } = storeToRefs(activityStore);

function onClick(activity: Activity) {
    activity.visible = !activity.visible;
}

function onRemove(activity: Activity) {
    console.log(activity);
    activityStore.remove(activity);
}
</script>

<template>
    <div class="activity-settings rounded p-3 no-highlight">
        <div class="activity-settings-content overflow-auto">
            <div v-for="activity in activities" :key="activity.id">
                <div class="activity-settings-item p-2 cursor-pointer" @click="onClick(activity)">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="w-100">
                            <font-awesome-icon
                                class="icon-check mr-1"
                                v-if="activity.visible"
                                icon="fas fa-check-square"
                                fa-fw />
                            <font-awesome-icon v-else class="mr-1" icon="far fa-square" fa-fw />
                            <small>
                                <icon class="mr-1" :icon="activity.icon" />
                                <span class="font-weight-bold">{{ activity.title || "No title available" }}</span>
                            </small>
                        </span>
                        <b-button
                            v-if="activity.mutable"
                            @click.stop="onRemove(activity)"
                            data-description="delete activity"
                            class="button-edit"
                            size="sm"
                            variant="link">
                            <font-awesome-icon icon="fa-trash" fa-fw />
                        </b-button>
                    </div>
                    <small>
                        {{ activity.description || "No description available" }}
                    </small>
                </div>
            </div>
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
    .button-edit {
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
    .button-edit {
        color: $brand-light;
    }
}
</style>
