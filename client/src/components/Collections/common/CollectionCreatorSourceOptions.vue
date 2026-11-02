<script setup lang="ts">
import { BFormGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

import GCheckbox from "@/components/BaseComponents/GCheckbox.vue";
import HelpText from "@/components/Help/HelpText.vue";

defineOptions({
    compatConfig: { COMPONENT_V_MODEL: false },
});

interface Props {
    modelValue: boolean;
    extensionsToggle?: boolean;
    renderExtensionsToggle?: boolean;
}

const props = defineProps<Props>();

const localHideSourceItems = ref(props.modelValue);

const emit = defineEmits<{
    (e: "update:modelValue", value: boolean): void;
    (e: "remove-extensions-toggle"): void;
}>();

// Watch for external updates to modelValue and sync with innerValue
watch(
    () => props.modelValue,
    (newValue) => {
        localHideSourceItems.value = newValue;
    },
);

watch(localHideSourceItems, (newValue) => {
    emit("update:modelValue", newValue);
});
</script>

<template>
    <BFormGroup class="inputs-form-group">
        <GCheckbox
            v-if="renderExtensionsToggle"
            name="remove-extensions"
            switch
            :model-value="extensionsToggle"
            @update:model-value="emit('remove-extensions-toggle')">
            {{ localize("Remove file extensions?") }}
        </GCheckbox>

        <GCheckbox
            v-model="localHideSourceItems"
            data-description="hide original elements"
            name="hide-originals"
            switch>
            <HelpText
                uri="galaxy.collections.collectionBuilder.hideOriginalElements"
                :text="localize('Hide original elements')" />
        </GCheckbox>
    </BFormGroup>
</template>
