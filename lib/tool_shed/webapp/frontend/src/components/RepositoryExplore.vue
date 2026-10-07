<script setup lang="ts">
import {
    faCircleInfo,
    faCodeBranch,
    faCodeCompare,
    faCompass,
    faFileCode,
    faHouse,
    faList,
} from "@fortawesome/free-solid-svg-icons"
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { GButton, GButtonGroup, GDropdownItem, GDropdownItemButton } from "@galaxyproject/galaxy-ui"
import { computed } from "vue"
import ActionMenu from "@/components/ActionMenu.vue"
import { contentsLocation, goToRepository, goToMetadataInspector } from "@/router"
import { useAuthStore } from "@/stores"

interface Repository {
    name: string
    owner: string
    id: string
    homepage_url?: string | null | undefined
    remote_repository_url?: string | null | undefined
    deprecated?: boolean
    deleted?: boolean
}

interface RepositoryExploreProps {
    repository: Repository
    // Only a revision the files API serves; null links the newest one
    browsableRevision?: string | null
    dense?: boolean
    showDetailsLink?: boolean
}

const props = withDefaults(defineProps<RepositoryExploreProps>(), {
    browsableRevision: null,
    dense: false,
    showDetailsLink: false,
})

const authStore = useAuthStore()

// hgweb's HTML views sit behind login (crawlers), so only offer the changelog to users who can open it
const changelog = computed(() =>
    authStore.user ? `/repos/${props.repository.owner}/${props.repository.name}/shortlog` : null,
)
// The files API 404s deprecated and deleted repositories
const contents = computed(() =>
    props.repository.deprecated || props.repository.deleted
        ? null
        : contentsLocation(props.repository.id, props.browsableRevision),
)
</script>
<template>
    <ActionMenu v-if="!dense" :icon="faCompass" label="Explore repository">
        <GDropdownItemButton v-if="showDetailsLink" @click="goToRepository(props.repository.id)">
            <FontAwesomeIcon :icon="faCircleInfo" fixed-width />
            Details
        </GDropdownItemButton>
        <GDropdownItem v-if="changelog" :href="changelog">
            <FontAwesomeIcon :icon="faCodeCompare" fixed-width />
            Changelog
        </GDropdownItem>
        <GDropdownItem v-if="contents" :to="contents">
            <FontAwesomeIcon :icon="faList" fixed-width />
            Contents
        </GDropdownItem>
        <GDropdownItemButton @click="goToMetadataInspector(props.repository.id)">
            <FontAwesomeIcon :icon="faFileCode" fixed-width />
            Metadata
        </GDropdownItemButton>
    </ActionMenu>
    <GButtonGroup v-else class="repository-explore-buttons">
        <GButton
            icon-only
            transparent
            title="Details"
            aria-label="Details"
            @click="goToRepository(props.repository.id)"
        >
            <FontAwesomeIcon :icon="faCircleInfo" />
        </GButton>
        <GButton
            icon-only
            transparent
            title="Metadata Inspector"
            aria-label="Metadata Inspector"
            @click="goToMetadataInspector(props.repository.id)"
        >
            <FontAwesomeIcon :icon="faFileCode" />
        </GButton>
        <GButton v-if="changelog" icon-only transparent title="Changelog" aria-label="Changelog" :href="changelog">
            <FontAwesomeIcon :icon="faCodeCompare" />
        </GButton>
        <GButton v-if="contents" icon-only transparent title="Contents" aria-label="Contents" :to="contents">
            <FontAwesomeIcon :icon="faList" />
        </GButton>
        <GButton
            v-if="repository.homepage_url"
            icon-only
            transparent
            title="Homepage"
            aria-label="Homepage"
            :href="repository.homepage_url"
        >
            <FontAwesomeIcon :icon="faHouse" />
        </GButton>
        <GButton
            v-if="repository.remote_repository_url"
            icon-only
            transparent
            title="Development Repository"
            aria-label="Development Repository"
            :href="repository.remote_repository_url"
        >
            <FontAwesomeIcon :icon="faCodeBranch" />
        </GButton>
    </GButtonGroup>
</template>

<style scoped lang="scss">
// .g-button keeps GButton's grey from outranking the brand tint these carried as q-btns
.repository-explore-buttons :deep(.g-button.g-transparent) {
    color: var(--color-galaxy-primary, #25537b);
}
</style>
