<script setup lang="ts">
import { computed, ref } from "vue";

import { KNOWN_COLLECTION_TYPES } from "@/components/Collections/common/knownCollectionTypes";
import { isValidCollectionTypeStr } from "@/components/Workflow/Editor/modules/collectionTypeDescription";

import GLink from "@/components/BaseComponents/GLink.vue";
import GModal from "@/components/BaseComponents/GModal.vue";
import CollectionTypeCards from "@/components/Collections/common/CollectionTypeCards.vue";
import FormElement from "@/components/Form/FormElement.vue";

interface Props {
    value?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onChange", collectionType: string | null): void;
}>();

const showHelp = ref(false);
// re-mounting the element after a pick from the dialog drops any custom text being typed, even when the
// pick is the saved type and so doesn't change the value
const elementKey = ref(0);

// a legacy "" means any collection type
const currentValue = computed(() => props.value || null);

const attributes = {
    data: [
        { label: "Any collection type", value: null },
        ...KNOWN_COLLECTION_TYPES.map((known) => ({
            label: `${known.label} (${known.collectionType})`,
            value: known.collectionType,
            help: known.description,
        })),
    ],
    other_label: "Custom collection type...",
    other_help:
        "Nest list, paired, paired_or_unpaired, and record with colons, from the outermost level in (e.g. list:list:paired).",
    validate: validateCollectionType,
};

function validateCollectionType(collectionType: string): string | undefined {
    if (!collectionType) {
        return "Enter a collection type such as list:list:paired.";
    } else if (!isValidCollectionTypeStr(collectionType)) {
        return "Invalid collection type";
    }
    return undefined;
}

const warning = computed(() => {
    if (!currentValue.value) {
        return "Typically, a value for this collection type should be specified.";
    }
    return undefined;
});

// Emits null, not undefined, for any collection type - an undefined value is dropped from the
// saved tool state and the server falls back to "list".
function onInput(collectionType: string | null) {
    emit("onChange", collectionType ?? null);
}

function onChooseFromHelp(collectionType: string) {
    showHelp.value = false;
    elementKey.value++;
    onInput(collectionType);
}
</script>

<template>
    <div class="form-collection-type">
        <FormElement
            id="collection_type"
            :key="elementKey"
            :value="currentValue"
            :attributes="attributes"
            :warning="warning"
            title="Collection type"
            type="select_or_text"
            @input="onInput" />
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
