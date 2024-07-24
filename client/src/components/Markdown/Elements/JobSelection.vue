<script setup lang="ts">
import { type SelectOption } from "./handlesMappingJobs";

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
            <b-navbar>
                <b-collapse id="nav-text-collapse" is-nav>
                    <b-navbar-nav>
                        <b-nav-text>Select Job</b-nav-text>
                    </b-navbar-nav>
                    <b-nav-form>
                        <b-input-group size="sm">
                            <b-form-select
                                :value="value"
                                class="text-right"
                                :options="selectJobOptions"
                                @input="handleInput"></b-form-select>
                        </b-input-group>
                    </b-nav-form>
                </b-collapse>
            </b-navbar>
            <slot />
        </div>
    </div>
</template>
