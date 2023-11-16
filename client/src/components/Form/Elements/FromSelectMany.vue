<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faLongArrowAltLeft, faLongArrowAltRight } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BFormInput, BInputGroup } from "bootstrap-vue";
import { type PropType, ref } from "vue";

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
    (e: "input", value: SelectValue | Array<SelectValue>): void;
}>();

const searchValue = ref("");
const useRegex = ref(false);
</script>

<template>
    <section :id="props.id" class="form-select-many">
        <BInputGroup>
            <BFormInput v-model="searchValue" :debounce="300" :placeholder="props.placeholder"></BFormInput>

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
                <BButton class="selection-button" title="Select all shown" variant="primary">
                    <FontAwesomeIcon icon="fa-long-arrow-alt-right" />
                </BButton>
            </div>
            <div class="options-list border-right"></div>
            <div class="selection-heading px-2">
                <span>Selected</span>
                <BButton class="selection-button" title="Deselect all shown" variant="primary">
                    <FontAwesomeIcon icon="fa-long-arrow-alt-left" />
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
        justify-content: space-between;

        .selection-button {
            height: 20px;
            width: 40px;
            padding: 0;
            display: grid;
            place-items: center;
        }
    }
}
</style>
