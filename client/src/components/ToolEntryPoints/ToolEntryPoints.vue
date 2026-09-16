<script setup lang="ts">
import {
    faCircle,
    faExternalLinkAlt,
    faLaptop,
    faLayerGroup,
    faMinus,
    faSpinner,
    type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, toRef } from "vue";

import type { CardAction, CardBadge } from "@/components/Common/GCard.types";
import { useJobDetails } from "@/composables/jobDetails";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { stateIsTerminal } from "@/utils/utils";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCard from "@/components/Common/GCard.vue";
import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    jobId: string;
}>();

const { entryPointsForJob } = storeToRefs(useEntryPointStore());
const { job } = useJobDetails(toRef(props, "jobId"));

const badges = computed<CardBadge[]>(() => {
    const total = entryPointsForJob.value(props.jobId).length;
    const active = entryPointsForJob.value(props.jobId).filter((entryPoint) => entryPoint.active).length;
    const label = total > 1 ? `${active}/${total} active` : `${active} active`;

    return [{ id: "entry-points-counter", label, variant: "outline-info", title: "" }];
});

const primaryActions = computed(() => {
    const actions: CardAction[] = [];
    if (entryPointsForJob.value(props.jobId).length === 1 && entryPointsForJob.value(props.jobId)[0]?.active) {
        const singularJob = entryPointsForJob.value(props.jobId)[0]!;
        actions.push({
            id: "go-to-interactive-tool",
            label: `Open ${singularJob.name}`,
            icon: faExternalLinkAlt,
            title: "Open in a new tab",
            href: singularJob.target,
            externalLink: true,
        });
    }
    return actions;
});

const secondaryActions: CardAction[] = [
    {
        id: "go-to-all-interactive-tools",
        label: "All Interactive Tools",
        icon: faLaptop,
        title: "Access all active Interactive Tools from the User menu",
        to: "/interactivetool_entry_points/list",
    },
];

const currentStatus = computed<{ title: string; icon: IconDefinition; class?: string }>(() => {
    if (entryPointsForJob.value(props.jobId).length === 0) {
        if (!job.value || !stateIsTerminal(job.value)) {
            return {
                title: "Waiting for Interactive Tool session(s) to become available",
                icon: faSpinner,
                class: "fa-spin",
            };
        } else {
            return {
                title: "No Interactive Tool sessions are currently available",
                icon: faMinus,
            };
        }
    } else if (entryPointsForJob.value(props.jobId).length === 1) {
        if (entryPointsForJob.value(props.jobId)[0]?.active) {
            return {
                title: "There is an Interactive Tool session available",
                icon: faCircle,
                class: "status-dot",
            };
        } else {
            return {
                title: "There is an Interactive Tool session available, waiting for it to become active",
                icon: faSpinner,
                class: "fa-spin",
            };
        }
    } else {
        return { title: "There are multiple Interactive Tool sessions available", icon: faLayerGroup };
    }
});
</script>

<template>
    <div class="job-info-section">
        <div class="job-info-section-icon">
            <FontAwesomeIcon :icon="faLaptop" />
        </div>
        <Heading inline size="sm" bold separator>Interactive Tools</Heading>

        <div class="job-info-section-spacer"></div>
        <GCard
            :content-class="currentStatus.class === 'fa-spin' ? 'entry-points-card-loading' : undefined"
            :badges="badges"
            :primary-actions="primaryActions"
            :secondary-actions="secondaryActions"
            :title="currentStatus.title"
            :title-icon="currentStatus"
            title-size="text">
            <template v-slot:description>
                <div v-if="entryPointsForJob(props.jobId).length > 1" class="entry-points-grid">
                    <GButton
                        v-for="entryPoint of entryPointsForJob(props.jobId)"
                        :key="entryPoint.id"
                        data-description="entry point button"
                        :disabled="!entryPoint.active"
                        :disabled-title="`${entryPoint.name} is waiting to become active...`"
                        :href="entryPoint.active ? entryPoint.target : undefined"
                        target="_blank"
                        rel="noopener"
                        color="blue"
                        outline
                        size="small"
                        title="Open in a new tab">
                        <div class="d-flex justify-content-between align-items-center flex-gapx-1 w-100">
                            <div class="d-flex align-items-center flex-gapx-1">
                                <FontAwesomeIcon
                                    fixed-width
                                    :class="{ 'status-dot': entryPoint.active }"
                                    :icon="entryPoint.active ? faCircle : faSpinner"
                                    :spin="!entryPoint.active" />
                                {{ entryPoint.name }}
                            </div>
                            <FontAwesomeIcon :icon="faExternalLinkAlt" />
                        </div>
                    </GButton>
                </div>
            </template>

            <template v-slot:update-time>
                <i
                    v-if="
                        entryPointsForJob(props.jobId).length > 1 &&
                        entryPointsForJob(props.jobId).some((ep) => !ep.active)
                    ">
                    Some sessions are not active yet
                </i>
            </template>
        </GCard>
    </div>
</template>

<style scoped lang="scss">
@import "@/components/JobInformation/job-info-section.scss";

.g-card {
    :deep(.entry-points-card-loading) {
        background-color: var(--color-blue-200);
    }
}

.entry-points-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 0.5rem;
    padding: 0.5rem 0.25rem;
}

:deep(.status-dot) {
    color: var(--color-green-600);
    transform: scale(0.4);
    box-shadow: 0 0 0 0.75em rgba(var(--color-green-600-rgb, 37, 163, 91), 0.15);
    border-radius: 50%;
}
</style>
