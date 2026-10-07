<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { findKnownCollectionType, KNOWN_COLLECTION_TYPES } from "@/components/Collections/common/knownCollectionTypes";
import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import CollectionTypeCards from "@/components/Collections/common/CollectionTypeCards.vue";
import FormElement from "@/components/Form/FormElement.vue";

const CUSTOM_COLLECTION_TYPE = "__custom__";

interface Props {
    value?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onChange", collectionType: string | null): void;
}>();

const currentValue = ref<string | undefined>(undefined);
const customMode = ref(false);
const showHelp = ref(false);

const selectOptions = [
    { label: "Any collection type", value: null },
    ...KNOWN_COLLECTION_TYPES.map((known) => ({
        label: `${known.label} (${known.collectionType})`,
        value: known.collectionType,
    })),
    { label: "Custom collection type...", value: CUSTOM_COLLECTION_TYPE },
];

const selectValue = computed(() => (customMode.value ? CUSTOM_COLLECTION_TYPE : currentValue.value || null));

const selectHelp = computed(() => {
    if (customMode.value) {
        return undefined;
    }
    return findKnownCollectionType(currentValue.value)?.description;
});

const warning = computed(() => {
    if (!currentValue.value && !customMode.value) {
        return "Typically, a value for this collection type should be specified.";
    }
    return undefined;
});

const customError = computed(() => {
    if (!currentValue.value) {
        return "Enter a collection type such as list:list:paired.";
    } else if (!isValidCollectionTypeStr(currentValue.value)) {
        return "Invalid collection type";
    }
    return undefined;
});

function updateValue(newValue: string | undefined) {
    currentValue.value = newValue;
    // The select cannot show a type it doesn't know, so such a value opens custom mode. A known
    // type doesn't close it - typing "list" on the way to "list:list" keeps the text field.
    if (newValue && !findKnownCollectionType(newValue)) {
        customMode.value = true;
    }
}

watch(() => props.value, updateValue, { immediate: true });

// Emits null, not undefined, for any collection type - an undefined value is dropped from the
// saved tool state and the server falls back to "list".
function emitCollectionType(newCollectionType: string | null) {
    currentValue.value = newCollectionType ?? undefined;
    emit("onChange", newCollectionType);
}

function onSelect(newValue: string | null) {
    if (newValue === CUSTOM_COLLECTION_TYPE) {
        customMode.value = true;
        return;
    }
    customMode.value = false;
    emitCollectionType(newValue);
}

function onCustomInput(newCollectionType: string | undefined) {
    if (!newCollectionType || !isValidCollectionTypeStr(newCollectionType)) {
        // keep the text so it can be corrected, but don't emit an empty or invalid collection type
        currentValue.value = newCollectionType;
        return;
    }
    emitCollectionType(newCollectionType);
}

function onChooseFromHelp(collectionType: string) {
    showHelp.value = false;
    customMode.value = false;
    emitCollectionType(collectionType);
}
</script>

<template>
    <div class="form-collection-type">
        <FormElement
            id="collection_type"
            :value="selectValue"
            :attributes="{ data: selectOptions }"
            :warning="warning"
            :help="selectHelp"
            title="Collection type"
            type="select"
            @input="onSelect" />
        <FormElement
            v-if="customMode"
            id="collection_type_custom"
            :value="currentValue"
            :error="customError"
            title="Custom collection type"
            help="Nest list, paired, paired_or_unpaired, and record with colons, from the outermost level in (e.g. list:list:paired)."
            type="text"
            @input="onCustomInput" />
        <div class="mb-3">
            <GLink data-description="collection type help" @click="showHelp = true">
                Not sure which collection type to use?
            </GLink>
        </div>
        <GModal v-model:show="showHelp" title="Collection Types" size="large">
            <p>
                Collections group datasets so a workflow can process many samples at once. Choose the structure this
                workflow input expects.
            </p>
            <CollectionTypeCards :value="currentValue" @select="onChooseFromHelp" />
        </GModal>
    </div>
</template>
