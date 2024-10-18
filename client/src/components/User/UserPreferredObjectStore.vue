<template>
    <UserPreferencesElement
        id="select-preferred-object-store"
        class="preferred-storage"
        :icon="faHdd"
        :title="title"
        :description="`Select a ${preferredOrEmptyString} storage location for the outputs of new jobs.`"
        @click="openModal">
        <BModal
            id="modal-select-preferred-object-store"
            ref="modal"
            v-model="showModal"
            centered
            :title="title"
            :title-tag="titleTag"
            hide-footer
            static
            :size="modalSize"
            @show="resetModal"
            @hidden="resetModal">
            <SelectObjectStore
                :parent-error="error"
                :for-what="newDatasetsDescription"
                :selected-object-store-id="selectedObjectStoreId"
                :default-option-title="galaxySelectionDefaultTitle"
                :default-option-description="galaxySelectionDefaultDescription"
                @onSubmit="handleSubmit" />
        </BModal>
    </UserPreferencesElement>
</template>

<script>
import { faHdd } from "@fortawesome/free-solid-svg-icons";
import axios from "axios";
import { BModal, VBModal } from "bootstrap-vue";
import SelectObjectStore from "components/ObjectStore/SelectObjectStore";
import { mapState } from "pinia";
import { prependPath } from "utils/redirect";
import { errorMessageAsString } from "utils/simple-error";
import Vue from "vue";

import { useConfigStore } from "@/stores/configurationStore";

import UserPreferencesElement from "./UserPreferencesElement.vue";

Vue.use(VBModal);

export default {
    components: {
        BModal,
        SelectObjectStore,
        UserPreferencesElement,
    },
    props: {
        userId: {
            type: String,
            required: true,
        },
        preferredObjectStoreId: {
            type: String,
            default: null,
        },
    },
    data() {
        return {
            error: null,
            popoverPlacement: "left",
            newDatasetsDescription: "New dataset outputs from tools and workflows",
            titleTag: "h3",
            modalSize: "sm",
            showModal: false,
            selectedObjectStoreId: this.preferredObjectStoreId,
            galaxySelectionDefaultTitle: "Use Galaxy Defaults",
            galaxySelectionDefaultDescription:
                "Selecting this will reset Galaxy to default behaviors configured by your Galaxy administrator.",
            faHdd,
        };
    },
    computed: {
        ...mapState(useConfigStore, ["config"]),
        preferredOrEmptyString() {
            if (this.config?.object_store_always_respect_user_selection) {
                return "";
            } else {
                return "Preferred";
            }
        },
        title() {
            return `${this.preferredOrEmptyString} Storage Location`;
        },
    },
    methods: {
        openModal() {
            this.$refs.modal.show();
        },
        resetModal() {},
        async handleSubmit(preferredObjectStoreId) {
            const payload = { preferred_object_store_id: preferredObjectStoreId };
            const url = prependPath("api/users/current");
            try {
                await axios.put(url, payload);
            } catch (e) {
                this.error = errorMessageAsString(e);
            }
            this.selectedObjectStoreId = preferredObjectStoreId;
            this.showModal = false;
        },
    },
};
</script>

<style scoped>
@import "user-styles.scss";
</style>
