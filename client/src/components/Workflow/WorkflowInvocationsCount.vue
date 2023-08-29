<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

library.add(faSitemap);

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
    <div>
        <span v-if="workflow.last_run_time">
            <BBadge v-b-tooltip.hover.left pill :title="localize('Last run')" variant="primary">
                <small>
                    last run
                    <UtcDate :date="workflow.last_run_time" mode="elapsed" />
                </small>
            </BBadge>
        </span>

        <BBadge
            v-b-tooltip.hover.left
            pill
            :title="localize('View workflow invocations')"
            href="#"
            variant="secondary"
            @click="onInvocations">
            <FontAwesomeIcon :icon="faSitemap" />
            <span v-if="workflow.run_count > 0"> workflow runs: {{ workflow.run_count }} </span>
            <span v-else> workflow never run </span>
        </BBadge>
    </div>
</template>
