<script setup lang="ts">
import { GAlert } from "@galaxyproject/galaxy-ui"
import { computed, ref, watch } from "vue"
import { getParsedTool, ParsedTool } from "@/api"
import { errorMessageAsString } from "@/util"
import LoadingDiv from "@/components/LoadingDiv.vue"
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
        <div v-if="linkedFromOlderRevision" class="newer-revision-notice">
            <!-- Page content rather than an event, so no assertive announcement -->
            <GAlert variant="warning" role="status">
                <strong
                    >Warning: Showing tool information from a newer repository revision (the latest repository revision
                    containing this tool version).</strong
                >
            </GAlert>
        </div>
        <loading-div v-if="loading" message="Loading tool information" />
        <div v-else-if="errorMessage">
            <error-banner :error="errorMessage" />
            <GAlert variant="info" class="stale-metadata-hint">
                <p>
                    This error may be caused by stale repository metadata. The repository owner or a Tool Shed
                    administrator can fix this by resetting the repository metadata.
                </p>
            </GAlert>
        </div>
        <section v-else class="tool-card">
            <header class="tool-card-header">
                <h1 class="tool-title">{{ toolTitle }}</h1>
                <div>{{ version }}</div>
            </header>
            <div class="tool-card-section">
                {{ tool?.description }}
            </div>
            <hr />
            <div class="tool-card-section">
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
                    <div v-for="edamOperation in tool?.edam_operations" :key="edamOperation" class="tool-detail">
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
            </div>
            <hr />
            <div v-if="xrefs.length > 0" class="tool-card-section">
                <h2 class="tool-section-heading">External links</h2>
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
            </div>
            <hr />
            <div class="tool-card-section">
                <h2 class="tool-section-heading">Help</h2>
                <preformatted-content :contents="tool?.help?.content ?? ''" />
            </div>
            <hr />
            <div class="tool-card-section">
                <h2 class="tool-section-heading">References</h2>
                <span v-if="citations.length < 1"><i>This tool does not define any references.</i></span>
                <dl v-else class="tool-details">
                    <div v-for="(citation, index) in tool?.citations" :key="index" class="tool-detail">
                        <dt>{{ citation.type }}</dt>
                        <dd>{{ citation.content }}</dd>
                    </div>
                </dl>
            </div>
        </section>
    </div>
</template>

<style scoped>
.tool-version-page {
    margin: var(--spacing-6);
}

.newer-revision-notice {
    margin-bottom: var(--spacing-4);
}

.stale-metadata-hint {
    margin-inline: var(--spacing-4);
}

.tool-card {
    background: var(--background-color);
    border: 1px solid var(--color-grey-300);
    border-radius: 0.25rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tool-card-header {
    padding: var(--spacing-4);
    background: var(--color-galaxy-primary);
    color: var(--background-color);
    border-radius: 0.25rem 0.25rem 0 0;
}

.tool-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 500;
    line-height: 2rem;
}

.tool-card-section {
    padding: var(--spacing-4);
}

.tool-details {
    margin: 0;
    border: 1px solid var(--color-grey-200);
}

.tool-detail {
    padding: var(--spacing-2) var(--spacing-4);
}

.tool-detail + .tool-detail {
    border-top: 1px solid var(--color-grey-200);
}

.tool-detail dt {
    color: var(--color-grey-600);
    font-size: var(--font-size-small);
    font-weight: 500;
    letter-spacing: 0.1em;
    line-height: 2;
}

.tool-detail dd {
    margin: 0;
}

.tool-section-heading {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 400;
    line-height: 2rem;
}
</style>
