<script setup lang="ts">
import { ref } from "vue";
import { useActivityStore } from "@/stores/activityStore";

const activityStore = useActivityStore();
const activities = ref(activityStore.getAll());
</script>

<template>
    <div class="activity-settings rounded p-3 no-highlight">
        <div class="activity-settings-content overflow-auto">
            <div v-for="activity in activities">
                <div class="p-2">
                    <b-form-checkbox :disabled="!activity.optional" v-model="activity.visible">
                        <small class="cursor-pointer">
                            <div>
                                <icon class="mr-1" :icon="activity.icon" />
                                <span class="font-weight-bold">{{ activity.title || "No title available" }}</span>
                            </div>
                            <div>
                                {{ activity.description || "No description available" }}
                            </div>
                        </small>
                    </b-form-checkbox>
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
</style>
