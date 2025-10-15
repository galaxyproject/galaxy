<script setup>
import { faExclamationCircle, faHdd, faKey } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BModal, BPopover } from "bootstrap-vue";
import Heading from "components/Common/Heading";
import FormMessage from "components/Form/FormMessage";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";
import { storeToRefs } from "pinia";
import { computed, onBeforeMount, ref, watch } from "vue";

import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useConfigStore } from "@/stores/configurationStore";
import { useToolsServiceCredentialsDefinitionsStore } from "@/stores/toolsServiceCredentialsDefinitionsStore";
import { useUserStore } from "@/stores/userStore";

import ToolSelectPreferredObjectStore from "./ToolSelectPreferredObjectStore";
import ToolTargetPreferredObjectStorePopover from "./ToolTargetPreferredObjectStorePopover";

import GButton from "../BaseComponents/GButton.vue";
import GButtonGroup from "../BaseComponents/GButtonGroup.vue";
import ToolCredentials from "./ToolCredentials.vue";
import ToolHelpForum from "./ToolHelpForum.vue";
import ToolTutorialRecommendations from "./ToolTutorialRecommendations.vue";
import FormCardSticky from "@/components/Form/FormCardSticky.vue";
import ToolFavoriteButton from "components/Tool/Buttons/ToolFavoriteButton.vue";
import ToolOptionsButton from "components/Tool/Buttons/ToolOptionsButton.vue";
import ToolVersionsButton from "components/Tool/Buttons/ToolVersionsButton.vue";

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
    version: {
        type: String,
        required: false,
        default: "1.0",
    },
    toolUuid: {
        type: String,
        default: null,
    },
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        required: false,
        default: "",
    },
    options: {
        type: Object,
        required: true,
    },
    messageText: {
        type: String,
        required: true,
    },
    messageVariant: {
        type: String,
        default: "info",
    },
    disabled: {
        type: Boolean,
        default: false,
    },
    allowObjectStoreSelection: {
        type: Boolean,
        default: false,
    },
    preferredObjectStoreId: {
        type: String,
        default: null,
    },
    /** If tool generated tours can be offered. */
    allowGeneratedTours: {
        type: Boolean,
        default: false,
    },
    allowEditingCredentials: {
        type: Boolean,
        default: false,
    },
});

const emit = defineEmits(["onChangeVersion", "updatePreferredObjectStoreId"]);

const { setToolServiceCredentialsDefinitionFor } = useToolsServiceCredentialsDefinitionsStore();

function onChangeVersion(v) {
    emit("onChangeVersion", v);
}

const errorText = ref(null);

watch(
    () => props.id,
    () => {
        errorText.value = null;
    },
);

const credentialToolTip = computed(() => {
    const credentialNames = props.options.credentials?.map((service) => service.name);
    if (!credentialNames.value) {
        return "";
    }

    return `This tool requires the following credentials when running the workflow: ${credentialNames.value.join(
        ", ",
    )}`;
});

const { isOnlyPreference } = useStorageLocationConfiguration();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const { isLoaded: isConfigLoaded, config } = storeToRefs(useConfigStore());
const hasUser = computed(() => !isAnonymous.value);
const versions = computed(() => props.options.versions);
const showVersions = computed(() => props.options.versions?.length > 1);

const storageLocationModalTitle = computed(() => {
    if (isOnlyPreference.value) {
        return "Tool Execution Preferred Storage";
    } else {
        return "Tool Execution Storage";
    }
});

const showPreferredObjectStoreModal = ref(false);
const toolPreferredObjectStoreId = ref(props.preferredObjectStoreId);

function onShowObjectStoreSelect() {
    showPreferredObjectStoreModal.value = true;
}

function onUpdatePreferredObjectStoreId(selectedToolPreferredObjectStoreId) {
    toolPreferredObjectStoreId.value = selectedToolPreferredObjectStoreId;
    emit("updatePreferredObjectStoreId", selectedToolPreferredObjectStoreId);
}

const showHelpForum = computed(() => isConfigLoaded.value && config.value.enable_help_forum_tool_panel_integration);

const canGenerateTours = computed(() =>
    Boolean(props.allowGeneratedTours && isConfigLoaded.value && config.value.enable_tool_generated_tours),
);

onBeforeMount(() => {
    if (props.options.credentials) {
        setToolServiceCredentialsDefinitionFor(props.id, props.version, props.options.credentials);
    }
});
</script>

<template>
    <FormCardSticky
        :error-message="errorText || ''"
        :description="props.description"
        :name="props.title"
        :version="props.version">
        <template v-slot:buttons>
            <GButtonGroup class="tool-card-buttons">
                <ToolFavoriteButton v-if="hasUser" :id="props.id" />
                <ToolVersionsButton
                    v-if="showVersions"
                    :version="props.version"
                    :versions="versions"
                    @onChangeVersion="onChangeVersion" />
                <ToolOptionsButton
                    :id="props.id"
                    :allow-generated-tours="canGenerateTours"
                    :tool-uuid="props.toolUuid"
                    :sharable-url="props.options.sharable_url"
                    :version="props.version"
                    :options="props.options" />
                <GButton
                    v-if="allowObjectStoreSelection"
                    id="tool-storage"
                    transparent
                    color="blue"
                    size="small"
                    class="float-right tool-storage"
                    @click="onShowObjectStoreSelect">
                    <FontAwesomeIcon :icon="faHdd" />
                </GButton>
                <ToolTargetPreferredObjectStorePopover
                    v-if="allowObjectStoreSelection"
                    :tool-preferred-object-store-id="toolPreferredObjectStoreId"
                    :user="currentUser" />
                <BModal
                    id="modal-select-preferred-object-store"
                    v-model="showPreferredObjectStoreModal"
                    :title="storageLocationModalTitle"
                    scrollable
                    centered
                    modal-class="tool-preferred-object-store-modal"
                    title-tag="h3"
                    size="lg"
                    ok-only
                    ok-title="Close">
                    <ToolSelectPreferredObjectStore
                        :tool-preferred-object-store-id="toolPreferredObjectStoreId"
                        @updated="onUpdatePreferredObjectStoreId" />
                </BModal>
            </GButtonGroup>
            <slot name="buttons" />
        </template>

        <template v-slot>
            <template v-if="props.options.credentials?.length">
                <ToolCredentials
                    v-if="!props.allowEditingCredentials"
                    class="mt-2"
                    :tool-id="props.id"
                    :tool-version="props.version"
                    :job-credentials-context="props.options.job_credentials_context" />
                <BAlert
                    v-else-if="props.allowEditingCredentials"
                    v-b-tooltip.hover
                    variant="info"
                    class="mt-2"
                    show
                    :title="credentialToolTip">
                    <FontAwesomeIcon :icon="faKey" />
                    Requires credentials to run this tool.

                    <FontAwesomeIcon id="target" :icon="faExclamationCircle" fixed-width />
                    <BPopover target="target" triggers="hover" boundary="window">
                        <div class="d-flex flex-column">
                            <span
                                v-for="(service, index) in props.options.credentials"
                                :key="index"
                                class="d-flex flex-column">
                                <b> {{ service.label }}: </b>
                                {{ service.description }}
                            </span>
                        </div>
                    </BPopover>
                </BAlert>
            </template>

            <FormMessage variant="danger" :message="errorText" :persistent="true" />
            <FormMessage :variant="props.messageVariant" :message="props.messageText" />
            <slot name="default" />
            <div v-if="props.disabled" class="portlet-backdrop" />
        </template>

        <template v-slot:footer>
            <slot name="buttons" />
            <div v-if="props.options.help" class="mt-2 mb-4">
                <Heading h2 separator bold size="sm">Help</Heading>
                <ToolHelp :content="props.options.help" :format="props.options.help_format" />
            </div>

            <ToolTutorialRecommendations
                :id="props.options.id"
                :name="props.options.name"
                :version="props.options.version"
                :owner="props.options.tool_shed_repository?.owner" />

            <ToolHelpForum v-if="showHelpForum" :tool-id="props.id" :tool-name="props.title" />

            <ToolFooter
                :id="props.id"
                :has-citations="props.options.citations"
                :xrefs="props.options.xrefs"
                :license="props.options.license"
                :creators="props.options.creator"
                :requirements="props.options.requirements" />
        </template>
    </FormCardSticky>
</template>

<style lang="scss" scoped>
.fa-wrench {
    cursor: unset;
}

.tool-card-buttons {
    height: 2em;
}

.portlet-backdrop {
    display: block;
}
</style>
