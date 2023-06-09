<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faFolderOpen } from "@fortawesome/free-solid-svg-icons";
import DataDialog from "../../DataDialog/DataDialog.vue";
import { computed, onMounted } from "vue";
import { getCurrentGalaxyHistory } from "../../../utils/data";
import { reactive } from "vue";

library.add(faFolderOpen);

interface DataDialogProps {
    id: string;
    multiple: boolean;
    value?: string;
}

const props = withDefaults(defineProps<DataDialogProps>(), {
    value: "",
    multiple: false,
});

const title = "Browse Datasets";
let historyID: string = "";
const localHistoryId = reactive({
    value: historyID,
});

onMounted(() => { 
    getCurrentGalaxyHistory().then((historyId) => {
        console.log("historyId", historyId);
        //set historyID to historyId
        localHistoryId.value = historyId;
    });
})

let initialODD = false;
const openDataDialog = reactive({
    value: initialODD,
});

const emit = defineEmits<{
    (e: "input", value: Object): void;
}>();

const currentValue = computed({
    get() {
        return Object(props.value);
    },
    set(newValue) {
        emit("input", newValue);
    },
});
</script>

<template>
    <div class="d-flex">
        <span @click="openDataDialog.value = true">
            <font-awesome-icon icon="folder-open" :title="title" />
            <b-form-input
                :id="id"
                v-model="currentValue"
                :class="['ui-text-area float-left disabled']" />
        </span>
        <DataDialog
            v-if="openDataDialog.value"
            v-model="currentValue"
            :history="localHistoryId.value"
            :multiple="multiple"
            @onCancel="openDataDialog.value = false"
            @onUpload="openDataDialog.value = false"
             />
    </div>
</template>
