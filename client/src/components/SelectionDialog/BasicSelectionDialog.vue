<template>
    <selection-dialog
        :error-message="errorMessage"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :hide-modal="onCancel">
        <template v-slot:search>
            <data-dialog-search v-model="filter" :title="title" />
        </template>
        <template v-slot:options>
            <data-dialog-table
                v-if="optionsShow"
                :items="items"
                :multiple="false"
                :is-encoded="isEncoded"
                :filter="filter"
                :leaf-icon="leafIcon"
                :show-details="!!detailsKey"
                @clicked="onOk"
                @load="load" />
        </template>
    </selection-dialog>
</template>

<script>
import SelectionDialogMixin from "./SelectionDialogMixin";
import { errorMessageAsString } from "utils/simple-error";

export default {
    mixins: [SelectionDialogMixin],
    props: {
        getData: {
            type: Function,
            required: true,
        },
        title: {
            type: String,
            required: true,
        },
        leafIcon: {
            type: String,
            default: null,
        },
        labelKey: {
            type: String,
            default: "id",
        },
        detailsKey: {
            type: String,
            default: null,
        },
        timeKey: {
            type: String,
            default: "update_time",
        },
        isEncoded: {
            type: Boolean,
            default: false,
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
    created() {
        this.load();
    },
    methods: {
        onOk(record) {
            this.$emit("onOk", record);
        },
        onCancel() {
            this.$emit("onCancel");
        },
        async load() {
            this.filter = null;
            this.optionsShow = false;
            try {
                const response = await this.getData();
                const items = response.data;
                this.items = items.map((item) => {
                    let timeStamp = item[this.timeKey];
                    if (timeStamp) {
                        const date = new Date(timeStamp);
                        timeStamp = date.toLocaleString("default", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            minute: "numeric",
                            hour: "numeric",
                        });
                    }
                    return {
                        id: item.id,
                        label: item[this.labelKey] || null,
                        details: item[this.detailsKey] || null,
                        time: timeStamp || null,
                        isLeaf: true,
                    };
                });
                this.optionsShow = true;
            } catch (err) {
                this.errorMessage = errorMessageAsString(err);
            }
        },
    },
};
</script>
