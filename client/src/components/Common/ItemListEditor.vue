<script setup lang="ts">
/**
 * Editable list of items: add/edit/remove (no duplictes/empty values)
 */
import { faEdit, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref } from "vue";

interface Props {
    itemName?: string;
    description?: string | null;
    itemFormat?: string | null;
    items?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    itemName: "item",
    description: null,
    itemFormat: null,
    items: () => [],
});

const emit = defineEmits<{
    (e: "onItems", items: string[]): void;
}>();

const itemsCurrent = computed(() => props.items || []);
const showForm = ref(false);
const editIndex = ref<number | null>(null);
const currentItem = ref<string | null>(null);
const currentItemError = ref<string | null>(null);

/** Start adding a new item. */
function onAdd() {
    showForm.value = true;
}

/** Start editing an item. */
function onEdit(index: number) {
    showForm.value = true;
    editIndex.value = index;
    currentItem.value = itemsCurrent.value[index] as string;
}

/** Remove an item. */
function onRemove(index: number) {
    const items = [...itemsCurrent.value];
    items.splice(index, 1);
    emit("onItems", items);
}

/** Save a new or existing item. */
function onSave() {
    if (validate()) {
        const itemValue = currentItem.value as string;
        const items = [...itemsCurrent.value];
        if (isNewItem()) {
            items.push(itemValue);
        } else {
            const i = editIndex.value as number;
            items[i] = itemValue;
        }
        resetForm();
        emit("onItems", items);
    }
}

/** Cancel editing. */
function onReset() {
    resetForm();
}

/** Validate an item. */
function validate() {
    // Check if item is not empty.
    const item = currentItem.value;
    if (!item) {
        currentItemError.value = "Please provide a value";
        return false;
    }
    // Check if item is unique.
    const foundIndex = itemsCurrent.value.indexOf(item);
    if (foundIndex > -1) {
        if (isNewItem() || (!isNewItem() && foundIndex != editIndex.value)) {
            currentItemError.value = `This ${props.itemName} has already been added`;
            return false;
        }
    }
    // Check format if regexp provided.
    if (props.itemFormat) {
        const re = new RegExp(props.itemFormat);
        if (!re.exec(item)) {
            currentItemError.value = `This ${props.itemName} has an invalid format`;
            return false;
        }
    }
    return true;
}

/** Are we adding a new item or editing an existing item. */
function isNewItem() {
    return editIndex.value === null;
}

/** Clear error message from current item. */
function removeErrorMessage() {
    currentItemError.value = null;
}

/** Reset and hide form.  */
function resetForm() {
    removeErrorMessage();
    editIndex.value = null;
    currentItem.value = null;
    showForm.value = false;
}
</script>

<template>
    <div>
        <div v-if="showForm">
            <b-input v-model="currentItem" :state="currentItemError ? false : null" @focus="removeErrorMessage" />
            <div class="spacer"></div>
            <div v-if="currentItemError" class="error">{{ currentItemError }}</div>
            <div v-if="props.description" v-html="description"></div>
            <b-button variant="primary" @click="onSave">Save</b-button>
            <b-button variant="danger" @click="onReset">Cancel</b-button>
        </div>
        <div v-else>
            <div v-if="itemsCurrent.length > 0">
                <div v-for="(item, index) in itemsCurrent" :key="index">
                    {{ item }}
                    <b-button
                        v-b-tooltip.hover
                        class="inline-icon-button"
                        variant="link"
                        size="sm"
                        :title="`Edit ${props.itemName}`"
                        @click="onEdit(index)">
                        <FontAwesomeIcon :icon="faEdit" />
                    </b-button>
                    <b-button
                        v-b-tooltip.hover
                        class="inline-icon-button"
                        variant="link"
                        size="sm"
                        :title="`Remove ${props.itemName}`"
                        @click="onRemove(index)">
                        <FontAwesomeIcon :icon="faTimes" />
                    </b-button>
                </div>
            </div>
            <i>
                <a href="#" @click.prevent="onAdd()">Add a new {{ itemName }}</a>
            </i>
        </div>
    </div>
</template>

<style lang="scss" scoped>
@import "@/style/scss/custom_theme_variables.scss";
.error {
    color: var(--color-red-500);
}
.spacer {
    padding: 5px;
}
</style>
