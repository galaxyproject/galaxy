<script setup>
import { useCurrentTheme } from "@/composables/user";
import { useConfig } from "@/composables/config";
import { computed, watch, ref } from "vue";
import { withPrefix } from "@/utils/redirect";
import Multiselect from "vue-multiselect";

const { currentTheme, setCurrentTheme } = useCurrentTheme();
const { config, isLoaded } = useConfig();

const show = ref(false);
const enableActivityBar = ref(false);
const currentValue = ref([]);

const formattedOptions = [
    {
        icon: "fa-upload",
        label: "Upload",
        value: "upload",
        description: "Allows users to upload data and observe progress",
    },
    {
        icon: "fa-upload",
        label: "Workflow",
        value: "workflow",
        description: "Access the workflow panel to search and execute workflows",
    },
    {
        icon: "fa-wrench",
        label: "Tools",
        value: "tools",
        description: "Access the workflow panel to search and execute workflows",
    },
    {
        icon: "fa-upload",
        label: "Invocations",
        value: "invocation",
        description: "Access the workflow panel to search and execute workflows",
    },
];

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
            :options="formattedOptions"
            :multiple="true"
            placeholder="Select activity"
            select-label="Click to select"
            track-by="value"
            label="label">
            <template slot="option" slot-scope="{ option }">
                <div>
                    <icon :icon="option.icon" />
                    {{ option.label }}
                </div>
                <div>
                    <small>
                        {{ option.description }}
                    </small>
                </div>
            </template>
        </multiselect>
    </b-card>
</template>
