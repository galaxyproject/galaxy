<script setup lang="ts">
import { BCard, BCollapse, BFormCheckbox, BFormGroup, BFormSelect, BLink } from "bootstrap-vue";
import { computed, reactive, ref } from "vue";

import { AVAILABLE_EXPORT_FORMATS } from "@/api/histories.export";
import type { ExportParams } from "@/components/Common/models/exportRecordModel";

interface Props {
    exportParams: ExportParams;
}

const props = defineProps<Props>();

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
        <BLink
            id="toggle-options-link"
            :class="isExpanded ? null : 'collapsed'"
            :aria-expanded="isExpanded ? 'true' : 'false'"
            aria-controls="collapse-options"
            @click="isExpanded = !isExpanded">
            {{ title }}
        </BLink>

        <BCollapse id="collapse-options" v-model="isExpanded">
            <BCard>
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
                    <BFormCheckbox
                        id="include-files-check"
                        v-model="localOptions.includeFiles"
                        switch
                        @change="onValueChanged">
                        Include Active
                    </BFormCheckbox>

                    <BFormCheckbox
                        id="include-deleted-check"
                        v-model="localOptions.includeDeleted"
                        switch
                        @change="onValueChanged">
                        Include Deleted (not purged)
                    </BFormCheckbox>

                    <BFormCheckbox
                        id="include-hidden-check"
                        v-model="localOptions.includeHidden"
                        switch
                        @change="onValueChanged">
                        Include Hidden
                    </BFormCheckbox>
                </BFormGroup>
            </BCard>
        </BCollapse>
    </div>
</template>
