<script setup lang="ts">
import { faPlay } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router/composables";

interface Props {
    id: string;
    full?: boolean;
    title?: string;
    disabled?: boolean;
    version?: number;
    force?: boolean;
    variant?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: undefined,
    version: undefined,
    variant: "primary",
});

const route = useRoute();
const router = useRouter();

const runPath = computed(
    () => `/workflows/run?id=${props.id}${props.version !== undefined ? `&version=${props.version}` : ""}`
);

function routeToPath() {
    if (props.force && route.fullPath === runPath.value) {
        // vue-router 4 supports a native force push with clean URLs,
        // but we're using a __vkey__ bit as a workaround
        // Only conditionally force to keep urls clean most of the time.
        // @ts-ignore - monkeypatched router, drop with migration.
        router.push(runPath.value, { force: true });
    } else {
        router.push(runPath.value);
    }
}
</script>

<template>
    <BButton
        id="workflow-run-button"
        v-b-tooltip.hover.top.html.noninteractive
        :title="title ?? '运行工作流'"
        :data-workflow-run="id"
        :variant="variant"
        size="sm"
        class="text-decoration-none"
        :disabled="disabled"
        :to="runPath"
        @click="routeToPath">
        <FontAwesomeIcon :icon="faPlay" fixed-width />

        <span v-if="full" v-localize>运行</span>
    </BButton>
</template>
