<script setup>
import { computed, ref, watch } from "vue";
import Activities from "./activities.js";

const activities = ref(Activities.slice().filter((a) => !!a.to));
</script>

<template>
    <div class="activity-settings rounded p-3">
        <div class="font-weight-bold">Select Activities:</div>
        <div class="activity-settings-content overflow-auto">
            <div v-for="option in activities">
                <div class="activity-item p-2">
                    <b-form-checkbox>
                        <small>
                            <div>
                                <icon class="mr-1" :icon="option.icon" />
                                <span class="font-weight-bold">{{ option.title || "No title available" }}</span>
                            </div>
                            <div>
                                {{ option.description || "No description available" }}
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

.activity-settings-content {
    max-height: 20rem;
}

.activity-item:hover {
    cursor: pointer;
    background: $brand-primary;
    color: $brand-light;
    border-radius: $border-radius-base;
}
</style>
