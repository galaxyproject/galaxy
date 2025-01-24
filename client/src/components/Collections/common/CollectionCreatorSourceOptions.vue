<script setup lang="ts">
import { BFormCheckbox, BFormGroup } from "bootstrap-vue";
import { ref, watch } from "vue";

import localize from "@/utils/localization";

import HelpText from "@/components/Help/HelpText.vue";

interface Props {
    value: boolean;
    extensionsToggle?: boolean;
    renderExtensionsToggle?: boolean;
}

const props = defineProps<Props>();

const localHideSourceItems = ref(props.value);

const emit = defineEmits<{
    (e: "input", value: boolean): void;
    (e: "remove-extensions-toggle"): void;
}>();

// Watch for external updates to value and sync with innerValue
watch(
    () => props.value,
    (newValue) => {
        localHideSourceItems.value = newValue;
    }
);

watch(localHideSourceItems, (newValue) => {
    emit("input", newValue);
});
</script>

<template>
    <BFormGroup class="inputs-form-group">
        <BFormCheckbox
            v-if="renderExtensionsToggle"
            name="remove-extensions"
            switch
            :checked="extensionsToggle"
            @input="emit('remove-extensions-toggle')">
            {{ localize("Remove file extensions?") }}
        </BFormCheckbox>

        <div data-description="hide original elements">
            <BFormCheckbox v-model="localHideSourceItems" name="hide-originals" switch>
                <HelpText
                    uri="galaxy.collections.collectionBuilder.hideOriginalElements"
                    :text="localize('Hide original elements')" />
            </BFormCheckbox>
        </div>
    </BFormGroup>
</template>
