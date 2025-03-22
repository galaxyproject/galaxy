<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEye, faEyeSlash, faKey, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { getGalaxyInstance } from "app";
import CopyToClipboard from "components/CopyToClipboard";
import UtcDate from "components/UtcDate";
import { ref } from "vue";

import svc from "./model/service";

library.add(faEye, faEyeSlash, faKey, faTrash);

defineProps({
    item: {
        type: Object,
        required: true,
    },
});

const emit = defineEmits(["getAPIKey"]);

const currentUserId = getGalaxyInstance().user.id;

const modal = ref(null);
const hover = ref(false);
const errorMessage = ref(null);

const toggleDeleteModal = () => {
    modal.value.toggle();
};
const deleteKey = () => {
    svc.deleteAPIKey(currentUserId)
        .then(() => emit("getAPIKey"))
        .catch((err) => (errorMessage.value = err.message));
};
</script>

<template>
    <b-card title="当前API密钥">
        <div class="d-flex justify-content-between w-100">
            <div class="w-100">
                <b-input-group class="w-100">
                    <b-input-group-prepend>
                        <b-input-group-text>
                            <icon icon="key" />
                        </b-input-group-text>
                    </b-input-group-prepend>

                    <b-input
                        :type="hover ? 'text' : 'password'"
                        :value="item.key"
                        disabled
                        data-test-id="api-key-input" />

                    <b-input-group-append>
                        <b-input-group-text>
                            <CopyToClipboard message="密钥已复制到剪贴板" :text="item.key" title="复制密钥" />
                        </b-input-group-text>

                        <b-button v-b-tooltip.hover title="显示/隐藏密钥" @click="hover = !hover">
                            <FontAwesomeIcon :icon="hover ? faEyeSlash : faEye" />
                        </b-button>

                        <b-button title="删除API密钥" @click="toggleDeleteModal">
                            <icon icon="trash" />
                        </b-button>
                    </b-input-group-append>
                </b-input-group>
                <span class="small text-black-50">
                    创建于
                    <UtcDate class="text-black-50 small" :date="item.create_time" mode="pretty" />
                </span>
            </div>
        </div>

        <b-modal ref="modal" title="删除API密钥" size="md" @ok="deleteKey">
            <p v-localize>您确定要删除此密钥吗？</p>
        </b-modal>
    </b-card>
</template>
