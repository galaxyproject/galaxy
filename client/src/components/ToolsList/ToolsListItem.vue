<script setup lang="ts">
import {
    faAngleDown,
    faAngleUp,
    faExclamationTriangle,
    faExternalLinkAlt,
    faUser,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

import { useFormattedToolHelp } from "@/composables/formattedToolHelp";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import ToolFavoriteButton from "@/components/Tool/Buttons/ToolFavoriteButton.vue";

// TODO: Refactor props to use defineProps with types (best practices)
const props = defineProps({
    id: { type: String, required: true },
    name: { type: String, required: true },
    section: { type: String, required: true },
    ontologies: { type: Array<string>, default: null },
    description: { type: String, default: null },
    summary: { type: String, default: null },
    help: { type: String, default: null },
    version: { type: String, default: null },
    link: { type: String, default: null },
    workflowCompatible: { type: Boolean, default: false },
    local: { type: Boolean, default: false },
    owner: { type: String, default: null },
});

// TODO: For tool open emit, consider adding event as param to allow for opening tool in new tab
const emit = defineEmits<{
    (e: "open"): void;
    (e: "apply-filter", filter: string, value: string): void;
}>();

const showHelp = ref(false);

const formattedToolHelp = computed(() => {
    if (showHelp.value) {
        const { formattedContent } = useFormattedToolHelp(props.help);
        return formattedContent.value;
    } else {
        return "";
    }
});

/** We add double quotes to the section filter since the backend Whoosh search
 * requires it for exact matches, and the `Filtering` class only does single quotes. */
const quotedSection = computed(() => (props.section ? `"${props.section}"` : ""));
</script>

<template>
    <div class="tool-list-item">
        <div class="top-bar bg-secondary px-2 py-1 rounded-right">
            <div class="py-1 d-flex flex-wrap flex-gapx-1">
                <span>
                    <FontAwesomeIcon v-if="props.local" :icon="faWrench" fixed-width />
                    <FontAwesomeIcon v-else :icon="faExternalLinkAlt" fixed-width />

                    <GLink v-if="props.local" dark @click="() => emit('open')">
                        <b>{{ props.name }}</b>
                    </GLink>
                    <GLink v-else dark :href="props.link">
                        <b>{{ props.name }}</b>
                    </GLink>
                </span>
                <span itemprop="description">{{ props.description }}</span>
                <span>(Galaxy Version {{ props.version }})</span>
            </div>
            <div class="d-flex align-items-start">
                <div class="d-flex align-items-center flex-gapx-1">
                    <ToolFavoriteButton :id="props.id" color="grey" />

                    <GButton
                        v-if="props.local"
                        class="text-nowrap"
                        color="blue"
                        size="small"
                        @click="() => emit('open')">
                        <FontAwesomeIcon :icon="faWrench" fixed-width />
                        Open
                    </GButton>
                    <GButton v-else class="text-nowrap" color="blue" size="small" :href="props.link">
                        <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                        Open
                    </GButton>
                </div>
            </div>
        </div>

        <div class="tool-list-item-content">
            <div class="d-flex flex-gapx-1 py-2">
                <span v-if="props.section" class="tag info">
                    <b>Section:</b>
                    <GLink thin @click="() => emit('apply-filter', 'section', quotedSection)">{{ section }}</GLink>
                </span>

                <span v-if="!props.local" class="tag info">
                    <FontAwesomeIcon :icon="faExternalLinkAlt" fixed-width />
                    External
                </span>

                <span v-if="!props.workflowCompatible" class="tag warn">
                    <FontAwesomeIcon :icon="faExclamationTriangle" />
                    Not Workflow compatible
                </span>

                <span v-if="props.owner" class="tag success">
                    <FontAwesomeIcon :icon="faUser" />
                    <b>Owner:</b>
                    <GLink thin @click="() => emit('apply-filter', 'owner', props.owner)">{{ props.owner }}</GLink>
                </span>

                <span v-if="props.ontologies && props.ontologies.length > 0">
                    <span v-for="ontology in props.ontologies" :key="ontology" class="tag toggle">
                        <GLink thin @click="() => emit('apply-filter', 'ontology', ontology)">{{ ontology }}</GLink>
                    </span>
                </span>
            </div>

            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-if="props.summary" v-html="props.summary"></div>

            <div v-if="props.help" class="mt-2">
                <GLink v-if="!showHelp" @click="() => (showHelp = true)">
                    <FontAwesomeIcon :icon="faAngleDown" />
                    Show tool help
                </GLink>
                <GLink v-else @click="() => (showHelp = false)">
                    <FontAwesomeIcon :icon="faAngleUp" />
                    Hide tool help
                </GLink>

                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-if="showHelp" class="mt-2" v-html="formattedToolHelp"></div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.tool-list-item {
    border-left: solid 3px $brand-secondary;
    border-radius: 0.25rem;

    .tool-list-item-content {
        padding-left: 0.5rem;
    }

    .tag {
        border-style: solid;
        border-width: 0 2px 1px 0;
        border-radius: 4px;
        padding: 0 0.5rem;
    }

    .info {
        background-color: scale-color($brand-info, $lightness: +75%);
        border-color: scale-color($brand-info, $lightness: +55%);
    }

    .success {
        background-color: scale-color($brand-success, $lightness: +75%);
        border-color: scale-color($brand-success, $lightness: +55%);
    }

    .warn {
        background-color: scale-color($brand-warning, $lightness: +75%);
        border-color: scale-color($brand-warning, $lightness: +55%);
    }

    .toggle {
        background-color: scale-color($brand-toggle, $lightness: +75%);
        border-color: scale-color($brand-toggle, $lightness: +55%);
    }

    .top-bar {
        display: flex;
        justify-content: space-between;
    }
}
</style>
