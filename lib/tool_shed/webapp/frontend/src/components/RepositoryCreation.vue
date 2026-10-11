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
                {{ repository.owner }} &middot; created
                <utc-date :date="repository.create_time" mode="elapsed" />
            </span>
        </router-link>
    </li>
</template>

<style scoped>
.repository-creation + .repository-creation {
    border-top: 1px solid var(--shed-border-subtle);
}

.repository-creation-link {
    position: relative;
    display: block;
    padding: 0.75rem 1.25rem;
    color: inherit;
    text-decoration: none;
    transition: background-color var(--shed-transition);
}

.repository-creation-link::before {
    content: "";
    position: absolute;
    inset: 0 auto 0 0;
    width: 3px;
    background: var(--shed-gold);
    transform: scaleY(0);
    transition: transform var(--shed-transition);
}

.repository-creation-link:hover {
    background: color-mix(in srgb, var(--shed-page-bg) 55%, white);
}

.repository-creation-link:hover::before {
    transform: scaleY(1);
}

.repository-creation-link:focus-visible {
    outline: 2px solid var(--color-galaxy-primary);
    outline-offset: -2px;
}

.repository-creation-name {
    display: block;
    font-weight: 700;
    color: var(--shed-link);
    overflow-wrap: anywhere;
}

.repository-creation-meta {
    display: block;
    margin-top: 0.1rem;
    color: var(--shed-muted);
    font-size: 0.82rem;
    overflow-wrap: anywhere;
}
</style>
