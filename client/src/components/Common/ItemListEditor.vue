<script setup lang="ts">
/**
 * Editable list of items: add/edit/remove (no duplictes/empty values)
 */
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import type { ComputedRef } from "vue";
import { computed, ref } from "vue";

interface Props {
    itemName?: string;
    items?: string[];
}

const props = withDefaults(defineProps<Props>(), {
    itemName: "item",
    items: () => [],
});

const emit = defineEmits<{
    (e: "onItems", items: string[]): void;
}>();

const itemsCurrent: ComputedRef<string[]> = computed(() => props.items);
const showForm = ref(false);
const editIndex = ref(null);
const currentItem = ref(null);
const currentItemError = ref(null);

/** Start adding a new item. */
function onAdd() {
    showForm.value = true;
}

/** Start editing an item. */
function onEdit(index) {
    showForm.value = true;
    editIndex.value = index;
    currentItem.value = itemsCurrent.value[index];
}

/** Remove an item. */
function onRemove(index) {
    const itms = [...itemsCurrent.value];
    itms.splice(index, 1);
    emit("onItems", itms);
}

/** Save a new or existing item. */
function onSave() {
    if (validate()) {
        const itms = [...itemsCurrent.value];
        if (isNewItem()) {
            itms.push(currentItem.value);
        } else {
            itms[editIndex.value] = currentItem.value;
        }
        resetForm();
        emit("onItems", itms);
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
            <b-input v-model="currentItem" :state="currentItemError ? false : null" @click="removeErrorMessage" />
            <div class="spacer"></div>
            <div v-if="currentItemError" class="error">{{ currentItemError }}</div>
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
                        <FontAwesomeIcon icon="edit" />
                    </b-button>
                    <b-button
                        v-b-tooltip.hover
                        class="inline-icon-button"
                        variant="link"
                        size="sm"
                        :title="`Remove ${props.itemName}`"
                        @click="onRemove(index)">
                        <FontAwesomeIcon icon="times" />
                    </b-button>
                </div>
            </div>
            <i>
                <a href="#" @click.prevent="onAdd()">Add a new {{ itemName }}</a>
            </i>
        </div>
    </div>
</template>

<style>
.error {
    color: red;
}
.spacer {
    padding: 5px;
}
</style>
