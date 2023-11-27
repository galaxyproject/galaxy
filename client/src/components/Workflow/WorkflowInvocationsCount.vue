<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { formatDistanceToNow, parseISO } from "date-fns";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

import UtcDate from "@/components/UtcDate.vue";

library.add(faClock, faSitemap);

interface Props {
    workflow: any;
}

const props = defineProps<Props>();

const router = useRouter();

function onInvocations() {
    router.push(`/workflows/${props.workflow.id}/invocations`);
}
</script>

<template>
    <div class="workflow-invocations-count d-flex align-items-center flex-gapx-1">
        <BBadge
            v-b-tooltip.hover
            pill
            :title="localize('View workflow invocations')"
            class="outline-badge cursor-pointer"
            @click="onInvocations">
            <FontAwesomeIcon :icon="faSitemap" />
            <span v-if="workflow.run_count > 0">
                <span class="compact-view">workflow runs:</span>
                {{ workflow.run_count }}
            </span>
            <span v-else>
                <span class="compact-view">workflow never run</span>
            </span>
        </BBadge>

        <BBadge
            v-if="workflow.last_run_time"
            v-b-tooltip.hover
            pill
            :title="`Last run: ${formatDistanceToNow(parseISO(`${workflow.last_run_time}Z`), {
                addSuffix: true,
            })}. Click to view details.`"
            class="outline-badge cursor-pointer">
            <FontAwesomeIcon :icon="faClock" />
            <span class="compact-view">last run:</span>
            <UtcDate :date="workflow.last_run_time" mode="elapsed" />
        </BBadge>
    </div>
</template>

<style scoped lang="scss">
@import "breakpoints.scss";

@container (max-width: #{$breakpoint-md}) {
    .compact-view {
        display: none;
    }
}
</style>
