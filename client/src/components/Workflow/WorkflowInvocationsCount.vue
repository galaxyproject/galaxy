<script setup lang="ts">
import { faList } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { computed } from "vue";

import type { StoredWorkflowDetailed } from "@/api/workflows";
import { useInvocationStore } from "@/stores/invocationStore";
import localize from "@/utils/localization";

import LoadingSpan from "../LoadingSpan.vue";

interface Props {
    workflow: StoredWorkflowDetailed;
}

const props = defineProps<Props>();

const invocationStore = useInvocationStore();

const count = computed(() => invocationStore.getInvocationCountByWorkflowId(props.workflow.id));
</script>

<template>
    <div class="workflow-invocations-count d-flex align-items-center flex-gapx-1">
        <BBadge v-if="count === null" pill>
            <LoadingSpan message="workflow runs:" />
        </BBadge>

        <BBadge v-else-if="count === 0" pill>
            <FontAwesomeIcon :icon="faList" fixed-width />
            <span>never run</span>
        </BBadge>

        <BBadge
            v-else-if="count > 0"
            v-b-tooltip.hover.noninteractive
            pill
            :title="localize('View workflow invocations')"
            class="outline-badge cursor-pointer"
            :to="`/workflows/${props.workflow.id}/invocations`">
            <FontAwesomeIcon :icon="faList" fixed-width />

            <span>
                workflow runs:
                {{ count }}
            </span>
        </BBadge>
    </div>
</template>
