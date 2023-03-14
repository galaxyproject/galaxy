<template>
    <b-row class="ml-3 mb-1">
        <i class="pref-icon pt-1 fa fa-lg fa-hdd" />
        <div class="pref-content pr-1">
            <a
                id="select-preferred-object-store"
                v-b-modal.modal-select-preferred-object-store
                class="preferred-storage"
                href="javascript:void(0)"
                ><b v-localize>Preferred Object Store</b></a
            >
            <div v-localize class="form-text text-muted">
                Select a preferred default object store for the outputs of new jobs to be created in.
            </div>
            <b-modal
                id="modal-select-preferred-object-store"
                ref="modal"
                v-model="showModal"
                centered
                title="Preferred Object Store"
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
            </b-modal>
        </div>
    </b-row>
</template>

<script>
import axios from "axios";
import { prependPath } from "utils/redirect";
import Vue from "vue";
import { BModal, BRow, VBModal } from "bootstrap-vue";
import SelectObjectStore from "components/ObjectStore/SelectObjectStore";
import { errorMessageAsString } from "utils/simple-error";

Vue.use(VBModal);

export default {
    components: {
        BModal,
        BRow,
        SelectObjectStore,
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
        };
    },
    methods: {
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
