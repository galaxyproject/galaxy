<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faClock, faSitemap } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useRouter } from "vue-router/composables";

import localize from "@/utils/localization";

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
        <BButton
            v-b-tooltip.hover
            :title="localize('View workflow invocations')"
            class="inline-icon-button"
            variant="link"
            size="sm"
            @click="onInvocations">
            <FontAwesomeIcon :icon="faSitemap" fixed-width />
        </BButton>
    </div>
</template>
