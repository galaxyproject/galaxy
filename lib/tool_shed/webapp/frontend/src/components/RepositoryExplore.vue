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
import { goToRepository, goToMetadataInspector } from "@/router"

interface Repository {
    name: string
    owner: string
    id: string
    homepage_url?: string | null | undefined
    remote_repository_url?: string | null | undefined
}

interface RepositoryExploreProps {
    repository: Repository
    currentRevision?: string | null
    dense?: boolean
    showDetailsLink?: boolean
}

const props = withDefaults(defineProps<RepositoryExploreProps>(), {
    currentRevision: null,
    dense: false,
    showDetailsLink: false,
})

const changelog = computed(() => `/repos/${props.repository.owner}/${[props.repository.name]}/shortlog`)
const contents = computed(() => `/repos/${props.repository.owner}/${[props.repository.name]}/file/tip`)
const hgwebLinks = computed(() => [
    { key: "changelog", icon: faCodeCompare, label: "Changelog", target: { href: changelog.value } },
    { key: "contents", icon: faList, label: "Contents", target: { href: contents.value } },
])
</script>
<template>
    <ActionMenu v-if="!dense" :icon="faCompass" label="Explore repository">
        <GDropdownItemButton v-if="showDetailsLink" @click="goToRepository(props.repository.id)">
            <FontAwesomeIcon :icon="faCircleInfo" fixed-width />
            Details
        </GDropdownItemButton>
        <GDropdownItem v-for="link in hgwebLinks" :key="link.key" v-bind="link.target">
            <FontAwesomeIcon :icon="link.icon" fixed-width />
            {{ link.label }}
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
        <GButton
            v-for="link in hgwebLinks"
            :key="link.key"
            icon-only
            transparent
            :title="link.label"
            :aria-label="link.label"
            v-bind="link.target"
        >
            <FontAwesomeIcon :icon="link.icon" />
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
