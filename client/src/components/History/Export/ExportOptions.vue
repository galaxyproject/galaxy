<script setup>
import { BFormGroup, BFormSelect } from "bootstrap-vue";
import { ExportParamsModel } from "components/Common/models/exportRecordModel";
import { computed, reactive, ref } from "vue";

import { GCard, GCollapse, GFormCheckbox, GLink } from "@/component-library";

import { AVAILABLE_EXPORT_FORMATS } from "./services";

const props = defineProps({
    exportParams: {
        type: ExportParamsModel,
        required: true,
    },
});

const emit = defineEmits(["onValueChanged"]);

const isExpanded = ref(false);
const title = computed(() => (isExpanded.value ? `Hide advanced export options` : `Show advanced export options`));
const localOptions = reactive({
    modelStoreFormat: props.exportParams.modelStoreFormat,
    includeFiles: props.exportParams.includeFiles,
    includeDeleted: props.exportParams.includeDeleted,
    includeHidden: props.exportParams.includeHidden,
});

function onValueChanged() {
    emit("onValueChanged", localOptions);
}
</script>

<template>
    <div>
        <GLink
            id="toggle-options-link"
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-options"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </GLink>
        <GCollapse id="collapse-options" v-model="isExpanded">
            <GCard>
                <BFormGroup label="Export Format:" label-for="format">
                    <BFormSelect
                        id="format-selector"
                        v-model="localOptions.modelStoreFormat"
                        :options="AVAILABLE_EXPORT_FORMATS"
                        value-field="id"
                        text-field="name"
                        @change="onValueChanged" />
                </BFormGroup>

                <BFormGroup label="Dataset files included in the package:">
                    <GFormCheckbox
                        id="include-files-check"
                        v-model="localOptions.includeFiles"
                        switch
                        @change="onValueChanged">
                        Include Active
                    </GFormCheckbox>

                    <GFormCheckbox
                        id="include-deleted-check"
                        v-model="localOptions.includeDeleted"
                        switch
                        @change="onValueChanged">
                        Include Deleted (not purged)
                    </GFormCheckbox>

                    <GFormCheckbox
                        id="include-hidden-check"
                        v-model="localOptions.includeHidden"
                        switch
                        @change="onValueChanged">
                        Include Hidden
                    </GFormCheckbox>
                </BFormGroup>
            </GCard>
        </GCollapse>
    </div>
</template>
