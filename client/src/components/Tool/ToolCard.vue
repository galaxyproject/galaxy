<script setup>
import FormMessage from "components/Form/FormMessage";
import ToolFavoriteButton from "components/Tool/Buttons/ToolFavoriteButton.vue";
import ToolVersionsButton from "components/Tool/Buttons/ToolVersionsButton.vue";
import ToolOptionsButton from "components/Tool/Buttons/ToolOptionsButton.vue";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";

import ariaAlert from "utils/ariaAlert";
import Webhooks from "utils/webhooks";
import { computed, ref, watch } from "vue";
import { useCurrentUser } from "composables/user";

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
    version: {
        type: String,
        required: false,
    },
    title: {
        type: String,
        required: true,
    },
    description: {
        type: String,
        required: false,
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
});

const emit = defineEmits(["onChangeVersion"]);

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

const { currentUser: user } = useCurrentUser();
const hasUser = computed(() => !user.value.isAnonymous);

const versions = computed(() => props.options.versions);
const showVersions = computed(() => props.options.versions?.length > 1);
</script>

<template>
    <div class="position-relative">
        <div class="sticky-top bg-secondary px-2 py-1 rounded">
            <div class="d-flex justify-content-between">
                <div class="py-1 d-flex flex-wrap flex-gapx-1">
                    <span>
                        <icon icon="wrench" class="fa-fw mr-1" />
                        <b itemprop="name">{{ title }}</b>
                    </span>
                    <span itemprop="description">{{ description }}</span>
                    <span>(Galaxy Version {{ version }})</span>
                </div>
                <b-button-group class="tool-card-buttons">
                    <ToolFavoriteButton v-if="hasUser" :id="props.id" @onSetError="onSetError" />
                    <ToolVersionsButton
                        v-if="showVersions"
                        :version="props.version"
                        :versions="versions"
                        @onChangeVersion="onChangeVersion" />
                    <ToolOptionsButton :id="props.id" :sharableUrl="props.options.sharable_url" />
                </b-button-group>
            </div>
        </div>

        <FormMessage variant="danger" :message="errorText" :persistent="true" />
        <FormMessage :variant="props.messageVariant" :message="props.messageText" />
        <slot name="body" />
        <div v-if="props.disabled" class="portlet-backdrop" />

        <div>
            <ToolHelp :content="props.options.help" />
            <ToolFooter
                :id="props.id"
                :has-citations="props.options.hasCitations"
                :xrefs="props.options.xrefs"
                :license="props.options.license"
                :creators="props.options.creators"
                :requirements="props.options.requirements" />
        </div>

        <div class="tool-buttons-row position-sticky d-flex justify-content-end float-right mt-2">
            <slot name="buttons" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
.fa-wrench {
    cursor: unset;
}

.tool-card-buttons {
    height: 2em;
}

.flex-gapx-1 {
    column-gap: 0.25em;
}

.sticky-top {
    z-index: 800;
}

.portlet-backdrop {
    display: block;
}

.tool-buttons-row {
    bottom: 0;
    column-gap: 0.5em;
}
</style>
