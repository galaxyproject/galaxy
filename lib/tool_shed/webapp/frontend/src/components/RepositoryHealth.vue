<script setup lang="ts">
import { faCalendar, faCircleCheck, faCircleXmark, faDownload } from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { computed } from "vue"
import { formatDistanceToNow, parseISO } from "date-fns"

interface RepositoryHealthProps {
    lastUpdated: string
    downloadable: boolean
    installs: number
}

const parsedDate = computed(() => parseISO(`${props.lastUpdated}Z`))
const elapsedTime = computed(() => formatDistanceToNow(parsedDate.value, { addSuffix: true }))
const props = defineProps<RepositoryHealthProps>()
</script>
<template>
    <!-- Shown inline rather than behind a menu: these are facts to read, not actions to take -->
    <ul class="repository-health" aria-label="Repository health">
        <li class="health-pill" :class="downloadable ? 'health-ok' : 'health-problem'">
            <FontAwesomeIcon :icon="downloadable ? faCircleCheck : faCircleXmark" />
            {{ downloadable ? "Downloadable" : "Not downloadable" }}
        </li>
        <li class="health-pill">
            <FontAwesomeIcon :icon="faDownload" />
            {{ installs }} {{ installs === 1 ? "install" : "installs" }}
        </li>
        <li class="health-pill">
            <FontAwesomeIcon :icon="faCalendar" />
            Updated {{ elapsedTime }}
        </li>
    </ul>
</template>

<style scoped lang="scss">
.repository-health {
    display: inline-flex;
    flex-wrap: wrap;
    gap: var(--spacing-2);
    margin: 0;
    padding: 0;
    list-style: none;
    vertical-align: middle;
}

.health-pill {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-1);
    padding: var(--spacing-1) var(--spacing-3);
    border-radius: 1rem;
    background-color: var(--color-grey-100);
    color: var(--color-grey-900);
    font-size: var(--font-size-small);

    &.health-ok svg {
        color: var(--color-green-700);
    }

    &.health-problem svg {
        color: var(--color-red-700);
    }
}
</style>
