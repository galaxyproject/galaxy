<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltLeft, faLongArrowAltRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup } from "bootstrap-vue";
import { computed, type PropType, ref } from "vue";

import { useFilterObjectArray } from "@/composables/filter";
import { useUid } from "@/composables/utils/uid";

library.add(faLongArrowAltLeft, faLongArrowAltRight);

type SelectValue = Record<string, unknown> | string | number | null;

interface SelectOption {
    label: string;
    value: SelectValue;
}

const props = defineProps({
    id: { type: String, default: useUid("form-select-many-").value },
    disabled: {
        type: Boolean,
        default: false,
    },
    optional: {
        type: Boolean,
        default: false,
    },
    options: {
        type: Array as PropType<Array<SelectOption>>,
        required: true,
    },
    placeholder: {
        type: String,
        default: "Search for options",
    },
    value: {
        type: String as PropType<SelectValue | SelectValue[]>,
        default: null,
    },
});

const _emit = defineEmits<{
    (e: "input", value: Array<SelectValue>): void;
}>();

const searchValue = ref("");
const useRegex = ref(false);

const searchRegex = computed(() => {
    if (useRegex.value) {
        try {
            const regex = new RegExp(searchValue.value);
            return regex;
        } catch (e) {
            return null;
        }
    } else {
        return null;
    }
});

const regexInvalid = computed(() => useRegex.value && searchRegex.value === null);
const asRegex = computed(() => searchRegex.value !== null);
const filteredOptions = useFilterObjectArray(props.options, searchValue, ["label"], asRegex);

const highlightedUnselected = ref([]);
const highlightedSelected = ref([]);

const selectText = computed(() => {
    if (highlightedUnselected.value.length > 0) {
        return "Select highlighted";
    } else if (searchValue.value === "") {
        return "Select all";
    } else {
        return "Select filtered";
    }
});

const deselectText = computed(() => {
    if (highlightedSelected.value.length > 0) {
        return "Deselect highlighted";
    } else if (searchValue.value === "") {
        return "Deselect all";
    } else {
        return "Deselect filtered";
    }
});
</script>

<template>
    <section :id="props.id" class="form-select-many">
        <BInputGroup>
            <BFormInput
                v-model="searchValue"
                :state="regexInvalid ? false : undefined"
                :debounce="300"
                :placeholder="props.placeholder"></BFormInput>

            <template v-slot:append>
                <BButton
                    :variant="useRegex ? 'primary' : 'outline-primary'"
                    role="switch"
                    :aria-checked="useRegex"
                    title="use regex"
                    @click="useRegex = !useRegex">
                    .*
                </BButton>
            </template>
        </BInputGroup>

        <div class="options-box border rounded p-2 mt-2">
            <div class="selection-heading border-right px-2">
                <span>Unselected</span>
                <BButton class="selection-button" :title="selectText" variant="primary">
                    {{ selectText }}
                    <FontAwesomeIcon icon="fa-long-arrow-alt-right" />
                </BButton>
            </div>
            <div class="options-list border-right">
                <div v-for="option in filteredOptions" :key="option.label">
                    {{ option.label }}
                </div>
            </div>
            <div class="selection-heading px-2">
                <span>Selected</span>
                <BButton class="selection-button" :title="deselectText" variant="primary">
                    <FontAwesomeIcon icon="fa-long-arrow-alt-left" />
                    {{ deselectText }}
                </BButton>
            </div>
            <div class="options-list"></div>
        </div>
    </section>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.options-box {
    resize: vertical;
    overflow: hidden;
    min-height: 200px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: auto 1fr;
    grid-auto-flow: column;

    .selection-heading {
        color: $gray-600;
        font-weight: bold;
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;

        .selection-button {
            height: 20px;
            padding: 0 0.5rem;
        }
    }
}
</style>
