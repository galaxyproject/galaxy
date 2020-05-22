<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="() => (modalShow = false)"
    >
        <template v-slot:search>
            <data-dialog-search v-model="filter" />
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="false"
                :filter="filter"
                leaf-icon="fa fa-sitemap fa-rotate-270"
                @clicked="clicked"
                @load="load"
            />
        </template>
    </selection-dialog>
</template>

<script>
import SelectionDialogMixin from "./SelectionDialogMixin";
import { Services } from "components/Workflow/services";

export default {
    mixins: [SelectionDialogMixin],
    props: {},
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
        this.services = new Services();
        this.load();
    },
    methods: {
        formatRows() {},
        clicked: function (record) {
            this.modalShow = false;
            this.callback(record);
        },
        /** Performs server request to retrieve data records **/
        load: function () {
            this.filter = null;
            this.optionsShow = false;
            this.services
                .getWorkflows()
                .then((items) => {
                    this.items = items.map((item) => {
                        return {
                            id: item.id,
                            label: item.name,
                            time: item.create_time,
                            isLeaf: true,
                        };
                    });
                    this.formatRows();
                    this.optionsShow = true;
                })
                .catch((errorMessage) => {
                    this.errorMessage = errorMessage.toString();
                });
        },
    },
};
</script>
