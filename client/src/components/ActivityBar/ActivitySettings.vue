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
                <div class="d-flex my-2">
                    <div>
                        <b-form-checkbox />
                    </div>
                    <div>
                        <div>
                            <icon class="mr-1" :icon="option.icon" />
                            <span class="font-weight-bold">{{ option.title || "No title available" }}</span>
                        </div>
                        <div>
                            {{ option.description || "No description available" }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<style lang="scss">
@import "theme/blue.scss";

.activity-settings {
    background: $brand-dark;
    width: 20rem;
}

.activity-settings-content {
    max-height: 20rem;
}
</style>
