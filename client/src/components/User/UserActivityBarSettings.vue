<script setup lang="ts">
import { computed, ref, type WritableComputedRef, type Ref } from "vue";
import { useUserStore } from "@/stores/userStore";
import Activities from "@/components/ActivityBar/activities.js";
import Multiselect from "vue-multiselect";

const userStore = useUserStore();

const show: Ref<Boolean> = ref(false);
const currentValue: Ref<Array<String>> = ref([]);

const enableActivityBar: WritableComputedRef<Boolean> = computed({
    get: () => {
        return userStore.showActivityBar;
    },
    set: () => {
        userStore.toggleActivityBar();
    },
});
</script>

<template>
    <b-card :show="show" class="user-activity-bar-settings mr-3">
        <b-form-checkbox v-model="enableActivityBar" switch>
            <b>Enable Activity Bar</b>
        </b-form-checkbox>
        <div class="font-weight-bold my-2">Select Activities:</div>
        <multiselect
            id="user-activity-bar-select"
            v-model="currentValue"
            :allow-empty="true"
            :close-on-select="false"
            :options="Activities.filter((a) => a.optional)"
            :multiple="true"
            placeholder="Select Activity"
            selected-label=""
            select-label=""
            deselect-label=""
            track-by="id"
            label="title">
            <template slot="option" slot-scope="{ option }">
                <div>
                    <small>
                        <icon class="mr-1" :icon="option.icon" />
                        <span class="font-weight-bold">{{ option.title || "No title available" }}</span>
                    </small>
                </div>
                <div>
                    <small>
                        {{ option.description || "No description available" }}
                    </small>
                </div>
            </template>
        </multiselect>
    </b-card>
</template>
