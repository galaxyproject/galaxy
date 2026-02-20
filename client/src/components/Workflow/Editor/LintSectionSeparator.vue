<script setup lang="ts">
import { faCheck, faExclamationTriangle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps<{
    sectionType: "critical" | "attributes";
    resolvedIssues: number;
    totalIssues: number;
}>();
</script>

<template>
    <!-- TODO: Ideally we want to use the same thing as the `.tool-panel-divider` from 
        https://github.com/bgruening/galaxy/commit/4b65bde448a1cc7d2f612ad0658f98b0fc64a0bc -->
    <div class="best-practices-lint-separator">
        <div>{{ props.sectionType.charAt(0).toUpperCase() + props.sectionType.slice(1) }} Best Practices</div>

        <div class="text-nowrap">
            <FontAwesomeIcon
                v-if="props.resolvedIssues === props.totalIssues"
                :icon="faCheck"
                class="text-success"
                :title="`All ${props.sectionType} best practices issues resolved!`" />
            <FontAwesomeIcon
                v-else
                :icon="faExclamationTriangle"
                class="text-danger"
                :title="`${props.resolvedIssues} out of ${props.totalIssues} ${props.sectionType} best practice issues resolved`" />
            {{ props.resolvedIssues }} / {{ props.totalIssues }}
        </div>
    </div>
</template>

<style scoped lang="scss">
.best-practices-lint-separator {
    align-items: center;
    display: flex;
    gap: 0.5rem;
    font-weight: 600;
    padding: 0.375rem 0.75rem;

    &::before,
    &::after {
        border-bottom: 1px solid currentColor;
        content: "";
        flex: 1;
        opacity: 0.35;
    }
}
</style>
