<script setup>
import FormMessage from "components/Form/FormMessage";
import ToolFavoriteButton from "components/Tool/Buttons/ToolFavoriteButton.vue";
import ToolVersionsButton from "components/Tool/Buttons/ToolVersionsButton.vue";
import ToolOptionsButton from "components/Tool/Buttons/ToolOptionsButton.vue";
import ToolFooter from "components/Tool/ToolFooter";
import ToolHelp from "components/Tool/ToolHelp";
import Heading from "components/Common/Heading";

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
        default: "1.0",
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

const { currentUser: user } = useCurrentUser(false, true);
const hasUser = computed(() => !user.value.isAnonymous);

const versions = computed(() => props.options.versions);
const showVersions = computed(() => props.options.versions?.length > 1);
</script>

<template>
    <div class="position-relative">
        <div class="underlay sticky-top" />
        <div class="tool-header sticky-top bg-secondary px-2 py-1 rounded">
            <div class="d-flex justify-content-between">
                <div class="py-1 d-flex flex-wrap flex-gapx-1">
                    <span>
                        <icon icon="wrench" class="fa-fw" />
                        <Heading h1 inline bold size="text" itemprop="name">{{ props.title }}</Heading>
                    </span>
                    <span itemprop="description">{{ props.description }}</span>
                    <span>(Galaxy Version {{ props.version }})</span>
                </div>
                <div class="d-flex flex-nowrap align-items-start flex-gapx-1">
                    <b-button-group class="tool-card-buttons">
                        <ToolFavoriteButton v-if="hasUser" :id="props.id" @onSetError="onSetError" />
                        <ToolVersionsButton
                            v-if="showVersions"
                            :version="props.version"
                            :versions="versions"
                            @onChangeVersion="onChangeVersion" />
                        <ToolOptionsButton
                            :id="props.id"
                            :sharable-url="props.options.sharable_url"
                            :options="props.options" />
                    </b-button-group>
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

        <div>
            <div class="mt-2 mb-4">
                <Heading h2 separator bold size="sm"> Help </Heading>
                <ToolHelp :content="props.options.help" />
            </div>

            <ToolFooter
                :id="props.id"
                :has-citations="props.options.citations"
                :xrefs="props.options.xrefs"
                :license="props.options.license"
                :creators="props.options.creators"
                :requirements="props.options.requirements" />
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "scss/theme/blue.scss";

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
