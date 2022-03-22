<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="onCancel">
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="false"
                :filter="filter"
                leaf-icon="fa fa-folder"
                @clicked="clicked"
                @load="load" />
        </template>
    </selection-dialog>
</template>

<script>
import axios from "axios";
import SelectionDialogMixin from "./SelectionDialogMixin";
import { getGalaxyInstance } from "app";
import { errorMessageAsString } from "utils/simple-error";

export default {
    mixins: [SelectionDialogMixin],
    props: {
        history: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            errorMessage: null,
            filter: null,
            items: [],
            modalShow: true,
            optionsShow: false,
            hasValue: false,
        };
    },
    created: function () {
        this.load();
    },
    methods: {
        formatRows() {},
        clicked: function (record) {
            this.modalShow = false;
            this.callback(record);
            this.$emit("onOk", record);
        },
        /** Called when the modal is hidden */
        onCancel() {
            this.modalShow = false;
            this.$emit("onCancel");
        },
        /** Performs server request to retrieve data records **/
        load: function () {
            this.filter = null;
            this.optionsShow = false;
            const Galaxy = getGalaxyInstance();
            const url = `${Galaxy.root}api/histories/${this.history}/contents?type=dataset_collection`;
            axios
                .get(url)
                .then((response) => {
                    this.items = response.data.map((item) => {
                        return {
                            id: item.id,
                            label: item.name,
                            time: item.created_time,
                            isLeaf: true,
                        };
                    });
                    this.formatRows();
                    this.optionsShow = true;
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessageAsString(errorMessage);
                });
        },
    },
};
</script>
