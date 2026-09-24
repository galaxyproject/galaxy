<script setup lang="ts">
import { computed } from "vue"
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
function navigate(location: string | null | undefined) {
    if (location) {
        window.location.href = location
    }
}
const buttonProperties = computed(() => {
    return {
        size: "sm",
        class: "text-primary",
        padding: "sm",
    }
})
</script>
<template>
    <q-fab
        class="q-px-md"
        color="secondary"
        text-color="primary"
        icon="explore"
        direction="down"
        aria-label="Explore repository"
        v-if="!dense"
    >
        <q-fab-action
            v-if="showDetailsLink"
            color="secondary"
            text-color="black"
            icon="sym_r_overview"
            label="Details"
            @click="goToRepository(props.repository.id)"
        />
        <!-- receipt_long? -->
        <q-fab-action
            color="secondary"
            text-color="black"
            icon="difference"
            label="Changelog"
            @click="navigate(changelog)"
        />
        <q-fab-action color="secondary" text-color="black" icon="list" label="Contents" @click="navigate(contents)" />
        <q-fab-action
            color="secondary"
            text-color="black"
            icon="sym_r_data_object"
            label="Metadata"
            @click="goToMetadataInspector(props.repository.id)"
        />
    </q-fab>
    <q-btn-group class="q-mx-xl" dense rounded push v-else>
        <q-btn
            v-bind="buttonProperties"
            icon="sym_r_overview"
            title="Details"
            aria-label="Details"
            @click="goToRepository(props.repository.id)"
        />
        <q-btn
            v-bind="buttonProperties"
            icon="sym_r_data_object"
            title="Metadata Inspector"
            aria-label="Metadata Inspector"
            @click="goToMetadataInspector(props.repository.id)"
        />
        <q-btn
            v-bind="buttonProperties"
            icon="difference"
            title="Changelog"
            aria-label="Changelog"
            @click="navigate(changelog)"
        />
        <q-btn
            v-bind="buttonProperties"
            icon="list"
            title="Contents"
            aria-label="Contents"
            @click="navigate(contents)"
        />
        <q-btn
            v-bind="buttonProperties"
            icon="home"
            title="Homepage"
            aria-label="Homepage"
            @click="navigate(repository.homepage_url)"
            v-if="repository.homepage_url"
        />
        <q-btn
            v-bind="buttonProperties"
            icon="code"
            title="Development Repository"
            aria-label="Development Repository"
            @click="navigate(repository.remote_repository_url)"
            v-if="repository.remote_repository_url"
        />
    </q-btn-group>
</template>
