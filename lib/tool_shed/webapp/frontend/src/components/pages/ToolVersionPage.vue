<script setup lang="ts">
import { GAlert } from "@galaxyproject/galaxy-ui"
import { computed, ref, watch } from "vue"
import { getParsedTool, ParsedTool } from "@/api"
import { errorMessageAsString } from "@/util"
import LoadingDiv from "@/components/LoadingDiv.vue"
import PageHeader from "@/components/PageHeader.vue"
import ErrorBanner from "@/components/ErrorBanner.vue"
import PreformattedContent from "@/components/PreformattedContent.vue"
import BioToolsLink from "@/components/BioToolsLink.vue"
import BioconductorLink from "@/components/BioconductorLink.vue"
import EdamLink from "@/components/EdamLink.vue"
import LicenseLink from "@/components/LicenseLink.vue"

interface Props {
    trsToolId: string
    version: string
    fromChangesetRevision?: string
}

const props = defineProps<Props>()

const tool = ref<ParsedTool>()
const loading = ref(true)
const errorMessage = ref<string | null>(null)

watch(
    props,
    async () => {
        loading.value = true
        errorMessage.value = null
        try {
            tool.value = await getParsedTool(props.trsToolId, props.version)
        } catch (e) {
            errorMessage.value = errorMessageAsString(e)
        }
        loading.value = false
    },
    { immediate: true },
)

const toolTitle = computed(() => {
    let title = props.trsToolId
    if (tool.value) {
        title = tool.value.name
    }
    return title
})

const citations = computed(() => {
    const citationEls = tool.value?.citations ?? []
    return citationEls
})

const xrefs = computed(() => {
    return tool.value?.xrefs ?? []
})

const repositoryRevision = computed(() => {
    return tool.value?.repository_revision
})

const repository = computed(() => {
    return repositoryRevision.value?.repository
})

const repositoryLink = computed(() => {
    const repoValue = repository.value
    const revisionValue = repositoryRevision.value
    if (repoValue && revisionValue) {
        return `/view/${repoValue.owner}/${repoValue.name}/${revisionValue.changeset_revision}`
    } else {
        return undefined
    }
})

const linkedFromOlderRevision = computed(() => {
    if (!repositoryRevision.value) {
        return false
    }
    if (!props.fromChangesetRevision) {
        return false
    }
    return repositoryRevision.value.changeset_revision != props.fromChangesetRevision
})
</script>

<template>
    <div class="tool-version-page">
        <loading-div v-if="loading" message="Loading tool information" class="tool-status" />
        <div v-else-if="errorMessage" class="tool-status">
            <error-banner :error="errorMessage" />
            <GAlert variant="info" class="stale-metadata-hint">
                <p>
                    This error may be caused by stale repository metadata. The repository owner or a Tool Shed
                    administrator can fix this by resetting the repository metadata.
                </p>
            </GAlert>
        </div>
        <template v-else>
            <page-header :title="toolTitle" :subtitle="tool?.description ?? undefined">
                <template v-if="repository && repositoryLink" #eyebrow>
                    <router-link :to="repositoryLink">{{ repository.owner }} / {{ repository.name }}</router-link>
                </template>
                <template #meta>
                    <span class="tool-version-chip">Version {{ version }}</span>
                </template>
            </page-header>
            <div class="tool-body">
                <div v-if="linkedFromOlderRevision" class="newer-revision-notice">
                    <!-- Page content rather than an event, so no assertive announcement -->
                    <GAlert variant="warning" role="status">
                        <strong
                            >Warning: Showing tool information from a newer repository revision (the latest repository
                            revision containing this tool version).</strong
                        >
                    </GAlert>
                </div>
                <div class="tool-main">
                    <section class="tool-card shed-card">
                        <h2 class="tool-section-heading shed-section-title">Help</h2>
                        <preformatted-content :contents="tool?.help?.content ?? ''" />
                    </section>
                    <section class="tool-card tool-references-card shed-card">
                        <h2 class="tool-section-heading shed-section-title">References</h2>
                        <p v-if="citations.length < 1" class="shed-muted">
                            <i>This tool does not define any references.</i>
                        </p>
                        <dl v-else class="tool-details">
                            <div v-for="(citation, index) in tool?.citations" :key="index" class="tool-detail">
                                <dt>{{ citation.type }}</dt>
                                <dd>{{ citation.content }}</dd>
                            </div>
                        </dl>
                    </section>
                </div>
                <aside class="tool-aside">
                    <section class="tool-card tool-details-card shed-card">
                        <h2 class="tool-section-heading shed-section-title">Details</h2>
                        <dl class="tool-details">
                            <div v-if="repository && repositoryRevision && repositoryLink" class="tool-detail">
                                <dt>Repository</dt>
                                <dd>
                                    <router-link :to="repositoryLink"
                                        >{{ repository.owner }} / {{ repository.name }} (@
                                        {{ repositoryRevision.changeset_revision }})</router-link
                                    >
                                </dd>
                            </div>
                            <div class="tool-detail">
                                <dt>TRS ID</dt>
                                <dd>{{ trsToolId }}</dd>
                            </div>
                            <div class="tool-detail">
                                <dt>LICENSE</dt>
                                <dd v-if="tool?.license">
                                    <license-link :id="tool.license" />
                                </dd>
                                <dd v-else><i>no license specified</i></dd>
                            </div>
                            <div class="tool-detail">
                                <dt>PROFILE</dt>
                                <dd v-if="tool?.profile">
                                    {{ tool.profile }}
                                </dd>
                                <dd v-else><i>no profile specified - default of 16.01 assumed</i></dd>
                            </div>
                            <div
                                v-for="edamOperation in tool?.edam_operations"
                                :key="edamOperation"
                                class="tool-detail"
                            >
                                <dt>EDAM OPERATION</dt>
                                <dd>
                                    <edam-link :term="edamOperation" />
                                </dd>
                            </div>
                            <div v-for="edamTopic in tool?.edam_topics" :key="edamTopic" class="tool-detail">
                                <dt>EDAM TOPIC</dt>
                                <dd>
                                    <edam-link :term="edamTopic" />
                                </dd>
                            </div>
                        </dl>
                    </section>
                    <section v-if="xrefs.length > 0" class="tool-card tool-xrefs-card shed-card">
                        <h2 class="tool-section-heading shed-section-title">External links</h2>
                        <dl class="tool-details">
                            <div v-for="xref in xrefs" :key="xref.value" class="tool-detail">
                                <dt>Catalog {{ xref.type }}</dt>
                                <dd v-if="xref.type == 'bio.tools'">
                                    <bio-tools-link :id="xref.value" />
                                </dd>
                                <dd v-else-if="xref.type == 'bioconductor'">
                                    <bioconductor-link :id="xref.value" />
                                </dd>
                                <dd v-else>
                                    {{ xref.value }}
                                </dd>
                            </div>
                        </dl>
                    </section>
                </aside>
            </div>
        </template>
    </div>
</template>

<style scoped>
.tool-status {
    max-width: var(--shed-content-width);
    margin: 2rem auto;
    padding: 0 1.5rem;
}

.stale-metadata-hint {
    margin-top: 1rem;
}

.tool-version-chip {
    padding: 0.25rem 0.75rem;
    font-size: 0.82rem;
    font-weight: 700;
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 999px;
}

/* Help and references lead; the details sit beside them on wide screens and below them on phones */
.tool-body {
    display: grid;
    grid-template-areas:
        "notice"
        "main"
        "aside";
    gap: 1.25rem;
    max-width: var(--shed-content-width);
    margin: 0 auto;
    padding: 1.75rem 1.5rem 3rem;
}

@media (min-width: 1024px) {
    .tool-body {
        grid-template-columns: minmax(0, 1fr) 22rem;
        grid-template-areas:
            "notice notice"
            "main aside";
        align-items: start;
    }
}

.newer-revision-notice {
    grid-area: notice;
}

.tool-aside {
    grid-area: aside;
}

.tool-main {
    grid-area: main;
}

.tool-aside,
.tool-main {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    min-width: 0;
}

.tool-card {
    padding: 1.25rem 1.5rem;
}

.tool-details {
    margin: 0;
}

.tool-detail {
    padding: 0.55rem 0;
}

.tool-detail + .tool-detail {
    border-top: 1px solid var(--shed-border-subtle);
}

.tool-detail dt {
    color: var(--shed-muted);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}

.tool-detail dd {
    margin: 0.1rem 0 0;
    overflow-wrap: anywhere;
}

.tool-card p {
    margin: 0;
}
</style>
