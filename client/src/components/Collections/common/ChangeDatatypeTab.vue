<script setup lang="ts">
import { computed, ref } from "vue";
import Multiselect from "vue-multiselect";

import localize from "@/utils/localization";

interface Props {
    // TODO: Replace with actual datatype type
    datatypes: any[];
    datatypeFromElements: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    // TODO: Replace with actual datatype type
    (e: "clicked-save", datatype: any): void;
}>();

const currentDatatype = ref(props.datatypeFromElements);
const selectedDatatype = ref(props.datatypes.find((element) => element.id == props.datatypeFromElements));

const hasSelectedDatatype = computed(() => {
    return Boolean(selectedDatatype.value);
});
const enableSave = computed(() => {
    return hasSelectedDatatype.value && selectedDatatype.value.id != currentDatatype.value;
});

function clickedSave() {
    emit("clicked-save", selectedDatatype.value);

    currentDatatype.value = selectedDatatype.value.id;
}
</script>

<template>
    <div>
        <div>
            <span class="float-left h-sm">Change Datatype/Extension of all elements in collection</span>

            <div class="text-right">
                <button class="save-datatype-edit btn btn-primary" :disabled="!enableSave" @click="clickedSave">
                    {{ localize("Save") }}
                </button>
            </div>
        </div>

        <b>{{ localize("New Type") }}: </b>

        <Multiselect
            v-if="hasSelectedDatatype"
            v-model="selectedDatatype"
            class="datatype-dropdown"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="datatypes"
            :searchable="true"
            :allow-empty="false">
            {{ selectedDatatype.text }}
        </Multiselect>
    </div>
</template>
