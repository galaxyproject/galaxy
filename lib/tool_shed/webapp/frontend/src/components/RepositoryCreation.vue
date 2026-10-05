<script setup lang="ts">
import UtcDate from "@/components/UtcDate.vue"

import type { Repository } from "@/api"

interface Props {
    repository: Repository
}

defineProps<Props>()
</script>

<template>
    <li class="repository-creation">
        <router-link v-if="repository" class="repository-creation-link" :to="`/repositories/${repository.id}`">
            <span class="repository-creation-name">{{ repository.name }}</span>
            <span class="repository-creation-meta">
                {{ repository.owner }}/{{ repository.name }} created
                <utc-date :date="repository.create_time" mode="elapsed" />
            </span>
        </router-link>
    </li>
</template>

<style scoped>
.repository-creation-link {
    display: block;
    padding: var(--spacing-2) var(--spacing-4);
    color: inherit;
    text-decoration: none;
}

.repository-creation-link:hover {
    background: var(--color-grey-100);
}

.repository-creation-link:focus-visible {
    outline: 2px solid var(--color-galaxy-primary);
    outline-offset: -2px;
}

.repository-creation-name {
    display: block;
    font-weight: 600;
}

.repository-creation-meta {
    display: block;
    color: var(--color-grey-600);
    font-size: var(--font-size-small);
}
</style>
