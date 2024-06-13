<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faHdd, faWrench } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BButtonGroup, BModal } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { useStorageLocationConfiguration } from "@/composables/storageLocation";
import { getAppRoot } from "@/onload/loadConfig";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import Heading from "@/components/Common/Heading.vue";
import FormMessage from "@/components/Form/FormMessage.vue";
import ToolFavoriteButton from "@/components/Tool/Buttons/ToolFavoriteButton.vue";
import ToolOptionsButton from "@/components/Tool/Buttons/ToolOptionsButton.vue";
import ToolVersionsButton from "@/components/Tool/Buttons/ToolVersionsButton.vue";
import ToolFooter from "@/components/Tool/ToolFooter.vue";
import ToolHelp from "@/components/Tool/ToolHelp.vue";
import ToolHelpForum from "@/components/Tool/ToolHelpForum.vue";
import ToolSelectPreferredObjectStore from "@/components/Tool/ToolSelectPreferredObjectStore.vue";
import ToolTargetPreferredObjectStorePopover from "@/components/Tool/ToolTargetPreferredObjectStorePopover.vue";
import ToolTutorialRecommendations from "@/components/Tool/ToolTutorialRecommendations.vue";

library.add(faHdd, faWrench);

interface Props {
    id: string;
    title: string;
    messageText: string;
    version?: string;
    stepError?: string;
    disabled?: boolean;
    description?: string;
    messageVariant?: string;
    preferredObjectStoreId?: string;
    options?: { [key: string]: any };
    allowObjectStoreSelection?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    version: "1.0",
    stepError: "Tool is not available",
    disabled: false,
    description: "",
    messageVariant: "info",
    preferredObjectStoreId: undefined,
    options: undefined,
    allowObjectStoreSelection: false,
});

const emit = defineEmits<{
    (e: "onChangeVersion", v: string): void;
    (e: "updatePreferredObjectStoreId", selectedToolPreferredObjectStoreId?: string): void;
}>();

const { isOnlyPreference } = useStorageLocationConfiguration();
const { currentUser, isAnonymous } = storeToRefs(useUserStore());
const { isLoaded: isConfigLoaded, config } = storeToRefs(useConfigStore());

const errorText = ref<string>("");
const showPreferredObjectStoreModal = ref(false);
const toolPreferredObjectStoreId = ref<string>(props.preferredObjectStoreId);

const root = computed(() => getAppRoot());
const hasUser = computed(() => !isAnonymous.value);
const versions = computed(() => props.options?.versions);
const showVersions = computed(() => props.options?.versions?.length > 1);
const showHelpForum = computed(() => isConfigLoaded.value && config.value.enable_help_forum_tool_panel_integration);
const storageLocationModalTitle = computed(() => {
    if (isOnlyPreference.value) {
        return "Tool Execution Preferred Storage Location";
    } else {
        return "Tool Execution Storage Location";
    }
});

function onSetError(e: string) {
    errorText.value = e;
}

function onChangeVersion(v: string) {
    emit("onChangeVersion", v);
}

function onShowObjectStoreSelect() {
    showPreferredObjectStoreModal.value = true;
}

function onUpdatePreferredObjectStoreId(selectedToolPreferredObjectStoreId: string) {
    showPreferredObjectStoreModal.value = false;
    toolPreferredObjectStoreId.value = selectedToolPreferredObjectStoreId;

    emit("updatePreferredObjectStoreId", selectedToolPreferredObjectStoreId);
}

watch(
    () => props.id,
    () => {
        errorText.value = "";
    }
);
</script>

<template>
    <div class="tool-card-container">
        <div class="underlay sticky-top" />

        <div v-if="!props.options?.id" class="sticky-top">
            <BAlert variant="danger" class="tool-header px-2 py-1" show>
                <span class="tool-header-name">
                    <FontAwesomeIcon :icon="faWrench" fixed-width />
                    {{ props.title }}
                </span>

                <span>
                    {{ props.stepError }}
                </span>
            </BAlert>
        </div>
        <div v-else class="sticky-top bg-secondary px-2 py-1 rounded">
            <div class="d-flex justify-content-between">
                <div class="py-1 d-flex flex-wrap flex-gapx-1">
                    <span>
                        <FontAwesomeIcon :icon="faWrench" fixed-width />

                        <Heading h1 inline bold size="text" itemprop="name">
                            {{ props.title || props.options?.name }}
                        </Heading>
                    </span>
                    <span itemprop="description">{{ props.description }}</span>
                    <span>(Galaxy Version {{ props.version }})</span>
                </div>

                <div class="d-flex flex-nowrap align-items-start flex-gapx-1">
                    <BButtonGroup class="tool-card-buttons">
                        <ToolFavoriteButton v-if="props.id && hasUser" :id="props.id" @onSetError="onSetError" />

                        <ToolVersionsButton
                            v-if="showVersions"
                            :version="props.version"
                            :versions="versions"
                            @onChangeVersion="onChangeVersion" />

                        <ToolOptionsButton
                            v-if="props.id"
                            :id="props.id"
                            :sharable-url="props.options?.sharable_url"
                            :options="props.options" />

                        <BButton
                            v-if="allowObjectStoreSelection"
                            id="tool-storage"
                            role="button"
                            variant="link"
                            size="sm"
                            class="float-right tool-storage"
                            @click="onShowObjectStoreSelect">
                            <FontAwesomeIcon :icon="faHdd" fixed-width />
                        </BButton>

                        <ToolTargetPreferredObjectStorePopover
                            v-if="allowObjectStoreSelection"
                            :tool-preferred-object-store-id="toolPreferredObjectStoreId"
                            :user="currentUser">
                        </ToolTargetPreferredObjectStorePopover>

                        <BModal
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
                        </BModal>
                    </BButtonGroup>

                    <slot name="header-buttons" />
                </div>
            </div>
        </div>

        <div id="tool-card-body">
            <FormMessage variant="danger" :message="errorText" :persistent="true" />

            <FormMessage :variant="props.messageVariant" :message="props.messageText" />

            <slot name="body" />

            <div v-if="props.disabled" class="portlet-backdrop" />
        </div>

        <slot name="buttons" />

        <div v-if="props.options">
            <div v-if="props.options.help" class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Help </Heading>

                <ToolHelp :content="props.options.help" />
            </div>

            <ToolTutorialRecommendations
                :id="props.options.id"
                :name="props.options.name"
                :version="props.options.version"
                :owner="props.options.tool_shed_repository?.owner" />

            <ToolHelpForum v-if="showHelpForum" :tool-id="props.options.id" :tool-name="props.title" />

            <ToolFooter
                :id="props.options.id"
                :has-citations="props.options.citations"
                :xrefs="props.options.xrefs"
                :license="props.options.license"
                :creators="props.options.creator"
                :requirements="props.options.requirements" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

.tool-card-container {
    .tool-header {
        display: flex;
        flex-direction: column;

        word-break: break-all;

        .tool-header-name {
            font-weight: bold;
        }
    }

    .underlay::after {
        content: "";
        display: block;
        position: absolute;
        top: -$margin-h;
        left: -0.5rem;
        right: -0.5rem;
        height: 50px;
        background: linear-gradient($white 75%, change-color($white, $alpha: 0));
    }

    .tool-card-buttons {
        height: 2em;
    }

    .portlet-backdrop {
        display: block;
    }
}
</style>
