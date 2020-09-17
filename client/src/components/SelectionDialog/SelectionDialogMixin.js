import DataDialogSearch from "./DataDialogSearch.vue";
import DataDialogTable from "./DataDialogTable.vue";
import SelectionDialog from "./SelectionDialog.vue";

export default {
    components: {
        "selection-dialog": SelectionDialog,
        "data-dialog-table": DataDialogTable,
        "data-dialog-search": DataDialogSearch,
    },
    props: {
        callback: {
            type: Function,
            default: () => {},
        },
    },
};
