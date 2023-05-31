<script setup>
import { useCurrentTheme } from "@/composables/user";
import { useConfig } from "@/composables/config";
import { useUserStore } from "@/stores/userStore";
import { computed, watch, ref } from "vue";
import { withPrefix } from "@/utils/redirect";
import Activities from "@/components/ActivityBar/activities.js";
import Multiselect from "vue-multiselect";

const userStore = useUserStore();
const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isLoaded } = useConfig();

const show = ref(false);
const currentValue = ref([]);

const enableActivityBar = computed({
    get: () => {
        return userStore.showActivityBar;
    },
    set: () => {
        userStore.toggleActivityBar();
    },
});

watch(
    () => isLoaded.value,
    () => {}
);
</script>

<template>
    <b-card :show="show" class="mr-3">
        <b-form-checkbox v-model="enableActivityBar" switch>
            <b>Enable Activity Bar</b>
        </b-form-checkbox>
        <div class="font-weight-bold my-2">Select Activities:</div>
        <multiselect
            v-model="currentValue"
            :allow-empty="true"
            :close-on-select="false"
            :options="Activities.filter((a) => a.optional)"
            :multiple="true"
            placeholder="Select activity"
            select-label="Click to select"
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
