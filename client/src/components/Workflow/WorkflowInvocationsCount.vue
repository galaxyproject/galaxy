<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BBadge } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

import UtcDate from "@/components/UtcDate.vue";

library.add(faEye, faSitemap);

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
    <div class="d-flex align-items-center flex-gapx-1">
        <BBadge
            v-b-tooltip.hover
            pill
            :title="localize('View workflow invocations')"
            href="#"
            variant="secondary"
            @click="onInvocations">
            <FontAwesomeIcon :icon="faSitemap" />
            <span v-if="workflow.run_count > 0"> workflow runs: {{ workflow.run_count }} </span>
            <span v-else> workflow never run </span>
        </BBadge>

        <BBadge v-if="workflow.last_run_time" v-b-tooltip.hover pill :title="localize('Last run')" variant="primary">
            <small>
                last run
                <UtcDate :date="workflow.last_run_time" mode="elapsed" />
            </small>
        </BBadge>
    </div>
</template>
