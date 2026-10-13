<script setup lang="ts">
import { BInputGroup, BNavbar, BNavbarNav, BNavForm, BNavText } from "bootstrap-vue";

import type { SelectOption } from "./handlesMappingJobs";

import GSelect from "@/components/BaseComponents/GSelect.vue";

interface JobSelectionProps {
    jobId?: string;
    implicitCollectionJobsId?: string;
    selectJobOptions: SelectOption[];
    value?: string;
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
                            <GSelect
                                aria-label="Select Job"
                                class="text-right"
                                size="small"
                                :model-value="value"
                                :options="selectJobOptions"
                                @update:model-value="handleInput" />
                        </BInputGroup>
                    </BNavForm>
                </div>
            </BNavbar>
            <slot />
        </div>
    </div>
</template>
