<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref, computed } from "vue";
import { useFormattedToolHelp } from "composables/formattedToolHelp";
import ToolFavoriteButton from "components/Tool/Buttons/ToolFavoriteButton";
const props = defineProps({
    id: { type: String, required: true },
    name: { type: String, required: true },
    section: { type: String, required: true },
    description: { type: String, default: null },
    summary: { type: String, default: null },
    help: { type: String, default: null },
    version: { type: String, default: null },
    link: { type: String, default: null },
    workflowCompatible: { type: Boolean, default: false },
    local: { type: Boolean, default: false },
});

const emit = defineEmits(["open"]);

const showHelp = ref(false);

const formattedToolHelp = computed(() => {
    if (showHelp.value) {
        const { formattedContent } = useFormattedToolHelp(props.help);
        return formattedContent.value;
    } else {
        return "";
    }
});
</script>

<script>
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faWrench,
    faExternalLinkAlt,
    faCheck,
    faTimes,
    faAngleDown,
    faAngleUp,
    faExclamationTriangle,
} from "@fortawesome/free-solid-svg-icons";

library.add(faWrench, faExternalLinkAlt, faCheck, faTimes, faAngleDown, faAngleUp, faExclamationTriangle);
</script>

<template>
    <div class="tool-list-item ui-portlet-section">
        <div class="top-bar bg-secondary px-2 py-1 rounded-right">
            <div class="py-1 d-flex flex-wrap flex-gapx-1">
                <span>
                    <FontAwesomeIcon v-if="props.local" icon="fa-wrench" fixed-width />
                    <FontAwesomeIcon v-else icon="fa-external-link-alt" fixed-width />

                    <b-button v-if="props.local" class="ui-link text-dark" @click="() => emit('open')">
                        <b>{{ props.name }}</b>
                    </b-button>
                    <b-button v-else class="ui-link text-dark" :href="props.link">
                        <b>{{ props.name }}</b>
                    </b-button>
                </span>
                <span itemprop="description">{{ props.description }}</span>
                <span>(Galaxy Version {{ props.version }})</span>
            </div>
            <div>
                <b-button-group>
                    <ToolFavoriteButton :id="props.id" />

                    <b-button
                        v-if="props.local"
                        class="text-nowrap"
                        variant="primary"
                        size="sm"
                        @click="() => emit('open')">
                        <FontAwesomeIcon icon="fa-wrench" fixed-width />
                        Open
                    </b-button>
                    <b-button v-else class="text-nowrap" variant="primary" size="sm" :href="props.link">
                        <FontAwesomeIcon icon="fa-external-link-alt" fixed-width />
                        Open
                    </b-button>
                </b-button-group>
            </div>
        </div>

        <div class="portlet-content">
            <div class="d-flex flex-gapx-1 py-2">
                <span v-if="props.section" class="info px-1 rounded">
                    <b>Section:</b> <b-link :to="`/tools/list?section=${props.section}`">{{ section }}</b-link>
                </span>

                <span v-if="!props.local" class="info px-1 rounded">
                    <FontAwesomeIcon icon="fa-external-link-alt" fixed-width />
                    External
                </span>

                <span v-if="!props.workflowCompatible" class="warn px-1 rounded">
                    <FontAwesomeIcon icon="fa-exclamation-triangle" />
                    Not Workflow compatible
                </span>
            </div>

            <div v-if="props.summary" v-html="props.summary"></div>

            <div v-if="props.help" class="mt-2">
                <b-button v-if="!showHelp" class="ui-link" @click="() => (showHelp = true)">
                    <FontAwesomeIcon icon="fa-angle-down" />
                    Show tool help
                </b-button>
                <b-button v-else class="ui-link" @click="() => (showHelp = false)">
                    <FontAwesomeIcon icon="fa-angle-up" />
                    Hide tool help
                </b-button>

                <div v-if="showHelp" class="mt-2" v-html="formattedToolHelp"></div>
            </div>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "theme/blue.scss";

.tool-list-item {
    .info {
        background-color: scale-color($brand-info, $lightness: +75%);
    }

    .success {
        background-color: scale-color($brand-success, $lightness: +75%);
    }

    .warn {
        background-color: scale-color($brand-warning, $lightness: +75%);
    }

    .top-bar {
        display: flex;
        justify-content: space-between;
    }
}
</style>
