<script setup>
import Heading from "components/Common/Heading";
import FormMessage from "components/Form/FormMessage";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";
import { getAppRoot } from "onload/loadConfig";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import ToolSelectPreferredObjectStore from "./ToolSelectPreferredObjectStore";
import ToolTargetPreferredObjectStorePopover from "./ToolTargetPreferredObjectStorePopover";

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
});

const emit = defineEmits(["onChangeVersion", "updatePreferredObjectStoreId"]);

function onChangeVersion(v) {
    emit("onChangeVersion", v);
}

const errorText = ref(null);

watch(
    () => props.id,
    () => {
        errorText.value = null;
    }
);

function onSetError(e) {
    errorText.value = e;
}

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

const root = computed(() => getAppRoot());
const showPreferredObjectStoreModal = ref(false);
const toolPreferredObjectStoreId = ref(props.preferredObjectStoreId);

function onShowObjectStoreSelect() {
    showPreferredObjectStoreModal.value = true;
}

function onUpdatePreferredObjectStoreId(selectedToolPreferredObjectStoreId) {
    showPreferredObjectStoreModal.value = false;
    toolPreferredObjectStoreId.value = selectedToolPreferredObjectStoreId;
    emit("updatePreferredObjectStoreId", selectedToolPreferredObjectStoreId);
}

const showHelpForum = computed(() => isConfigLoaded.value && config.value.enable_help_forum_tool_panel_integration);
</script>

<template>
    <FormCardSticky
        :error-message="errorText || ''"
        :description="props.description"
        :name="props.title"
        :version="props.version">
        <template v-slot:buttons>
            <b-button-group class="tool-card-buttons">
                <ToolFavoriteButton v-if="hasUser" :id="props.id" @onSetError="onSetError" />
                <ToolVersionsButton
                    v-if="showVersions"
                    :version="props.version"
                    :versions="versions"
                    @onChangeVersion="onChangeVersion" />
                <ToolOptionsButton
                    :id="props.id"
                    :tool-uuid="props.toolUuid"
                    :sharable-url="props.options.sharable_url"
                    :options="props.options" />
                <b-button
                    v-if="allowObjectStoreSelection"
                    id="tool-storage"
                    role="button"
                    variant="link"
                    size="sm"
                    class="float-right tool-storage"
                    @click="onShowObjectStoreSelect">
                    <span class="fa fa-hdd" />
                </b-button>
                <ToolTargetPreferredObjectStorePopover
                    v-if="allowObjectStoreSelection"
                    :tool-preferred-object-store-id="toolPreferredObjectStoreId"
                    :user="currentUser" />
                <b-modal
                    v-model="showPreferredObjectStoreModal"
                    :title="storageLocationModalTitle"
                    modal-class="tool-preferred-object-store-modal"
                    title-tag="h3"
                    size="sm"
                    hide-footer>
                    <ToolSelectPreferredObjectStore
                        :tool-preferred-object-store-id="toolPreferredObjectStoreId"
                        :root="root"
                        @updated="onUpdatePreferredObjectStoreId" />
                </b-modal>
            </b-button-group>
            <slot name="buttons" />
        </template>

        <template v-slot>
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
