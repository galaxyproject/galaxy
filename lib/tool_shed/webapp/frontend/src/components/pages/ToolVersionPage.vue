<script setup lang="ts">
import { computed, ref, watch } from "vue"
import { getParsedTool, ParsedTool } from "@/api"
import LoadingDiv from "@/components/LoadingDiv.vue"
import PreformattedContent from "@/components/PreformattedContent.vue"
import BioToolsLink from "@/components/BioToolsLink.vue"
import BioconductorLink from "@/components/BioconductorLink.vue"
import EdamLink from "@/components/EdamLink.vue"
import LicenseLink from "@/components/LicenseLink.vue"

interface Props {
    trsToolId: string
    version: string
}

const props = defineProps<Props>()

const tool = ref<ParsedTool>()
const loading = ref(true)

watch(
    props,
    async () => {
        loading.value = true
        tool.value = await getParsedTool(props.trsToolId, props.version)
        loading.value = false
    },
    { immediate: true }
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
</script>

<template>
    <q-page class="q-ma-lg">
        <loading-div v-if="loading" message="Loading tool information" />
        <q-card v-else>
            <q-card-section class="bg-primary text-white col-grow">
                <div class="text-h6">{{ toolTitle }}</div>
                <div class="text-subtitle">{{ version }}</div>
            </q-card-section>
            <q-card-section>
                {{ tool?.description }}
            </q-card-section>
            <q-separator />
            <q-card-section>
                <q-list bordered separator>
                    <q-item>
                        <q-item-section>
                            <q-item-label overline>TRS ID</q-item-label>
                            <q-item-label>{{ trsToolId }}</q-item-label>
                        </q-item-section>
                    </q-item>
                    <q-item>
                        <q-item-section>
                            <q-item-label overline>LICENSE</q-item-label>
                            <q-item-label v-if="tool?.license">
                                <license-link :id="tool.license" />
                            </q-item-label>
                            <q-item-label v-else><i>no license specified</i></q-item-label>
                        </q-item-section>
                    </q-item>
                    <q-item v-for="xref in tool?.xrefs || []" :key="xref.value">
                        <q-item-section>
                            <q-item-label overline>REFERENCE {{ xref.reftype }}</q-item-label>
                            <q-item-label v-if="xref.reftype == 'bio.tools'">
                                <bio-tools-link :id="xref.value" />
                            </q-item-label>
                            <q-item-label v-else-if="xref.reftype == 'bioconductor'">
                                <bioconductor-link :id="xref.value" />
                            </q-item-label>
                            <q-item-label v-else>
                                {{ xref.value }}
                            </q-item-label>
                        </q-item-section>
                    </q-item>
                    <q-item v-for="edamOperation in tool?.edam_operations" :key="edamOperation">
                        <q-item-section>
                            <q-item-label overline>EDAM OPERATION</q-item-label>
                            <q-item-label>
                                <edam-link :term="edamOperation" />
                            </q-item-label>
                        </q-item-section>
                    </q-item>
                    <q-item v-for="edamTopic in tool?.edam_topics" :key="edamTopic">
                        <q-item-section>
                            <q-item-label overline>EDAM TOPIC</q-item-label>
                            <q-item-label>
                                <edam-link :term="edamTopic" />
                            </q-item-label>
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-card-section>
            <q-separator />
            <q-card-section>
                <div class="text-h5 q-mr-lg">Help</div>
                <preformatted-content :contents="tool?.help?.content ?? ''" />
            </q-card-section>
            <q-separator />
            <q-card-section>
                <div class="text-h5 q-mr-lg">Citations</div>
                <span v-if="citations.length < 1"><i>This tool does not define any citations.</i></span>
                <q-list bordered separator v-else>
                    <q-item v-for="(citation, index) in tool?.citations" :key="index">
                        <q-item-section>
                            <q-item-label overline>{{ citation.type }}</q-item-label>
                            <q-item-label>{{ citation.content }}</q-item-label>
                        </q-item-section>
                    </q-item>
                </q-list>
            </q-card-section>
        </q-card>
    </q-page>
</template>
