<script setup lang="ts">
import { storeToRefs } from "pinia";
import { useActivityStore } from "@/stores/activityStore";
import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faSquare } from "@fortawesome/free-regular-svg-icons";
import { faCheckSquare } from "@fortawesome/free-solid-svg-icons";

library.add({
    faSquare,
    faCheckSquare,
});

const activityStore = useActivityStore();
const { activities } = storeToRefs(activityStore);

function onClick(activity: any) {
    activity.visible = !activity.visible;
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
                        <b-button-group>
                            <b-button
                                v-if="activity.mutable"
                                v-b-tooltip.bottom.hover
                                class="create-hist-btn"
                                @click.stop
                                data-description="create new history"
                                size="sm"
                                variant="link"
                                :title="'Edit' | l">
                                <icon fixed-width icon="edit" />
                            </b-button>
                            <b-button
                                v-if="activity.mutable"
                                v-b-modal.selector-history-modal
                                v-b-tooltip.bottom.hover
                                @click.stop
                                data-description="switch to another history"
                                size="sm"
                                variant="link"
                                :title="'Delete' | l">
                                <icon fixed-width icon="trash" />
                            </b-button>
                        </b-button-group>
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
}
.activity-settings-item:hover {
    background: $brand-primary;
    color: $brand-light;
    border-radius: $border-radius-large;
    .icon-check {
        color: $brand-light;
    }
}
</style>
