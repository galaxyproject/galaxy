<script setup lang="ts">
import { BFormSelect, BInputGroup, BNavbar, BNavbarNav, BNavForm, BNavText } from "bootstrap-vue";

import type { SelectOption } from "./handlesMappingJobs";

interface JobSelectionProps {
    jobId?: string;
    implicitCollectionJobsId?: string;
    selectJobOptions: SelectOption[];
    value?: String | undefined;
}

const emit = defineEmits<{
    (e: "input", id: string | undefined): void;
}>();

function handleInput(value: string | undefined) {
    emit("input", value);
}
defineProps<JobSelectionProps>();
</script>

<template>
    <div>
        <slot v-if="jobId"> </slot>
        <div v-else>
            <BNavbar>
                <div class="navbar-collapse">
                    <BNavbarNav>
                        <BNavText>Select Job</BNavText>
                    </BNavbarNav>
                    <BNavForm>
                        <BInputGroup size="sm">
                            <BFormSelect
                                :value="value"
                                class="text-right"
                                :options="selectJobOptions"
                                @input="handleInput"></BFormSelect>
                        </BInputGroup>
                    </BNavForm>
                </div>
            </BNavbar>
            <slot />
        </div>
    </div>
</template>
