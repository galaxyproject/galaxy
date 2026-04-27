<script setup lang="ts">
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventBus } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import localize from "@/utils/localization";

import GLink from "@/components/BaseComponents/GLink.vue";

const { emit } = useEventBus<string>("open-tool-section");

const router = useRouter();

const props = withDefaults(
    defineProps<{
        message?: string;
        writable?: boolean;
    }>(),
    {
        message: "This history is empty.",
        writable: true,
    },
);

const { openGlobalUploadModal } = useGlobalUploadModal();
function clickDataLink() {
    emit("getext");
    router.push("/upload/data-source-tools");
}
</script>

<template>
    <BAlert show>
        <h4 id="empty-history-message" class="mb-1">
            <FontAwesomeIcon :icon="faInfoCircle" />
            <span>{{ localize(message) }}</span>
        </h4>

        <p v-if="props.writable">
            <GLink inline @click.prevent="openGlobalUploadModal">You can load your own data</GLink>
            <span v-localize>or</span>
            <GLink inline @click.prevent="clickDataLink">get data from an external source</GLink>
        </p>
    </BAlert>
</template>
