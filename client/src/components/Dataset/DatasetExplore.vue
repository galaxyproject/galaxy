<script setup lang="ts">
import { faChevronDown, faChevronRight, faTools } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

import { type DatatypeConverter, fetchDatatypeConverters } from "@/api/datatypes";
import { fetchToolDataInputs, type ToolDataInput } from "@/api/tools";
import { useUid } from "@/composables/utils/uid";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useToolStore } from "@/stores/toolStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { filterLatestToolVersions } from "@/utils/tool-version";

import { type InteractiveToolMatch, matchInteractiveTools } from "./interactiveToolMatching";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import ButtonPlain from "@/components/Common/ButtonPlain.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /**
     * Id of the dataset to launch interactive tools with
     */
    datasetId: string;
    /**
     * Datatype extension of the dataset, matched against the tools' data inputs
     */
    datasetExtension: string;
}

interface ExploreTool {
    id: string;
    name: string;
    description: string;
    version: string;
    icon?: string;
    inputName: string | null;
    match: InteractiveToolMatch;
}

const props = defineProps<Props>();

const router = useRouter();
const toolStore = useToolStore();
const datatypesMapperStore = useDatatypesMapperStore();

const genericListId = useUid("dataset-explore-generic-");

const toolsLoaded = ref(false);
const converters = ref<DatatypeConverter[] | null>(null);
const dataInputsById = ref<Record<string, ToolDataInput[]>>({});
const errorMessage = ref("");
const query = ref("");
const genericExpanded = ref(false);

// The mapper may still be loading for another component, so wait for it reactively.
const loading = computed(
    () => !errorMessage.value && (!toolsLoaded.value || !converters.value || !datatypesMapperStore.datatypesMapper),
);

const tools = computed<ExploreTool[]>(() => {
    const mapper = datatypesMapperStore.datatypesMapper;
    if (!toolsLoaded.value || !converters.value || !mapper) {
        return [];
    }
    const interactiveTools = filterLatestToolVersions(toolStore.getInteractiveTools());
    return matchInteractiveTools(
        interactiveTools,
        dataInputsById.value,
        props.datasetExtension,
        mapper,
        converters.value,
    ).map(({ tool, inputName, match }) => ({
        id: tool.id,
        name: tool.name,
        description: tool.description,
        version: tool.version,
        icon: tool.icon,
        inputName,
        match,
    }));
});

const searching = computed(() => Boolean(query.value.trim()));

const filteredTools = computed(() => {
    const queryLower = query.value.trim().toLowerCase();
    if (!queryLower) {
        return tools.value;
    }
    return tools.value.filter(
        (tool) =>
            tool.name.toLowerCase().includes(queryLower) ||
            Boolean(tool.description?.toLowerCase().includes(queryLower)),
    );
});

const specificTools = computed(() => filteredTools.value.filter((tool) => tool.match !== "generic"));

const genericTools = computed(() => filteredTools.value.filter((tool) => tool.match === "generic"));

// Search hits stay visible: the group is forced open while searching and the user's choice returns after.
const showGeneric = computed(() => genericExpanded.value || searching.value);

const emptyMessage = computed(() => `No interactive tools accept '${props.datasetExtension}' on this server.`);

const groups = computed(() =>
    [
        { key: "specific", tools: specificTools.value, collapsible: false },
        { key: "generic", tools: genericTools.value, collapsible: true },
    ].filter((group) => group.tools.length > 0),
);

function iconUrl(tool: ExploreTool) {
    return `${getAppRoot()}api/tools/${encodeURIComponent(tool.id)}/icon`;
}

function launchTool(tool: ExploreTool) {
    let url = `/?tool_id=${encodeURIComponent(tool.id)}&version=${encodeURIComponent(tool.version)}`;
    if (tool.inputName) {
        url += `&${encodeURIComponent(tool.inputName)}=${encodeURIComponent(props.datasetId)}`;
    }
    router.push(url);
}

async function loadTools() {
    try {
        const [, loadedDataInputs, loadedConverters] = await Promise.all([
            toolStore.fetchTools(),
            fetchToolDataInputs("interactive"),
            fetchDatatypeConverters(),
            datatypesMapperStore.createMapper(),
        ]);
        dataInputsById.value = loadedDataInputs;
        converters.value = loadedConverters;
        toolsLoaded.value = true;
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    }
}

loadTools();
</script>

<template>
    <div class="dataset-explore p-2">
        <p class="mb-2">
            Launch an interactive app with this dataset. Apps run as jobs and appear under Interactive Tools.
        </p>

        <LoadingSpan v-if="loading" message="Loading interactive tools" />
        <GAlert v-else-if="errorMessage" variant="danger">{{ errorMessage }}</GAlert>
        <p v-else-if="tools.length === 0" class="dataset-explore-empty text-muted">{{ emptyMessage }}</p>
        <div v-else>
            <DelayedInput :delay="100" class="my-2" placeholder="search interactive tools" @change="query = $event" />

            <p v-if="groups.length === 0" class="dataset-explore-no-match text-muted">
                No interactive tools match your search.
            </p>

            <div v-for="group in groups" :key="group.key" :class="`dataset-explore-${group.key}`">
                <GButton
                    v-if="group.collapsible"
                    transparent
                    class="dataset-explore-generic-toggle my-1"
                    title="Interactive tools that accept any datatype"
                    disabled-title="Expanded while searching"
                    :disabled="searching"
                    :aria-controls="genericListId"
                    :aria-expanded="String(showGeneric)"
                    @click="genericExpanded = !genericExpanded">
                    <FontAwesomeIcon :icon="showGeneric ? faChevronDown : faChevronRight" fixed-width />
                    General-purpose ({{ group.tools.length }})
                </GButton>

                <div v-show="!group.collapsible || showGeneric" :id="group.collapsible ? genericListId : undefined">
                    <ButtonPlain
                        v-for="tool in group.tools"
                        :key="tool.id"
                        class="dataset-explore-item d-flex align-items-center rounded p-2"
                        :data-tool-id="tool.id"
                        :data-match="tool.match"
                        @click="launchTool(tool)">
                        <div class="dataset-explore-icon mr-2">
                            <img v-if="tool.icon" :src="iconUrl(tool)" alt="" />
                            <FontAwesomeIcon v-else :icon="faTools" size="2x" />
                        </div>

                        <div class="flex-grow-1 text-break">
                            <div class="font-weight-bold">{{ tool.name }}</div>
                            <div v-if="tool.description" class="text-muted">{{ tool.description }}</div>
                        </div>

                        <div class="d-flex flex-column align-items-end ml-2 text-nowrap">
                            <small v-if="tool.match === 'converted'" class="dataset-explore-converted text-muted">
                                via conversion
                            </small>
                            <small v-if="!tool.inputName" class="dataset-explore-no-prefill text-muted">
                                select dataset in form
                            </small>
                        </div>
                    </ButtonPlain>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.dataset-explore-item:hover {
    background: $gray-200;
}

.dataset-explore-icon {
    color: $gray-600;
    width: 3rem;
    min-width: 3rem;
    height: 3rem;
    display: flex;
    align-items: center;
    justify-content: center;

    img {
        width: 3rem;
        max-height: 3rem;
    }
}
</style>
