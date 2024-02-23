<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

library.add(faPlay);

interface Props {
    id: string;
    full?: boolean;
}

const props = defineProps<Props>();

const router = useRouter();

function ExecuteWorkflow() {
    router.push(`/workflows/run?id=${props.id}`);
}
</script>

<template>
    <BButton
        id="workflow-run-button"
        v-b-tooltip.hover.top.noninteractive
        title="Run workflow"
        :data-workflow-run="id"
        variant="primary"
        size="sm"
        @click.stop="ExecuteWorkflow">
        <FontAwesomeIcon :icon="faPlay" />
        <span v-if="full" v-localize>Run</span>
    </BButton>
</template>
