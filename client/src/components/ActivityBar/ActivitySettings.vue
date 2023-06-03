<script setup>
import { computed, ref, watch } from "vue";
import Activities from "./activities.js";

const activities = ref(Activities.slice().filter((a) => !!a.to));
</script>

<template>
    <div>
        <div class="font-weight-bold my-2">Select Activities:</div>
        <div class="overflow-auto" style="max-height: 10rem">
            <div v-for="option in activities">
                <div class="d-flex my-2">
                    <div>
                        <b-form-checkbox switch />
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

.activity-bar {
    background: $panel-bg-color;
}

.activity-bar::-webkit-scrollbar {
    display: none;
}

.activity-chosen-class {
    background: $brand-secondary;
    border-radius: $border-radius-extralarge;
}

.activity-drag-class {
    display: none;
}

.activity-popper-disabled {
    .popper-element {
        display: none;
    }
}

.panels-enter-active,
.panels-leave-active {
    transition: all 0.3s;
}

.panels-enter,
.panels-leave-to {
    transform: translateX(-100%);
}

.vertical-overflow {
    overflow-y: auto;
    overflow-x: hidden;
}
</style>
