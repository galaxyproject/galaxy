<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faInfoCircle } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useEventBus } from "@vueuse/core";
import { BAlert } from "bootstrap-vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import localize from "@/utils/localization";

library.add(faInfoCircle);

const { emit } = useEventBus<string>("open-tool-section");

const props = withDefaults(
    defineProps<{
        message?: string;
        writable?: boolean;
    }>(),
    {
        message: "该历史记录为空。",
        writable: true,
    }
);

const { openGlobalUploadModal } = useGlobalUploadModal();
function clickDataLink() {
    emit("getext");
}
</script>

<template>
    <BAlert show>
        <h4 id="empty-history-message" class="mb-1">
            <FontAwesomeIcon :icon="faInfoCircle" />
            <span>{{ localize(message) }}</span>
        </h4>

        <p v-if="props.writable">
            <a v-localize href="#" @click.prevent="openGlobalUploadModal">您可以上传自己的数据</a>
            <span v-localize>或</span>
            <a v-localize href="#" @click.prevent="clickDataLink">从外部来源获取数据</a>。
        </p>
    </BAlert>
</template>
