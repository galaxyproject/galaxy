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
// Sits on the dark page header, so the pills are glassy light-on-dark
.repository-health {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
    vertical-align: middle;
}

.health-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.75rem;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 999px;
    background-color: rgba(255, 255, 255, 0.08);
    color: #fff;
    font-size: 0.82rem;
    font-weight: 700;

    svg {
        color: var(--color-ebony-clay-200, #bbc0d2);
    }

    &.health-ok svg {
        color: var(--color-green-400);
    }

    &.health-problem svg {
        color: var(--color-red-400);
    }
}
</style>
