<script setup lang="ts">
import { faEdit, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { ref } from "vue";

import type { BasedOnWork } from "@/api/workflows";

import BasedOnForm from "./BasedOnForm.vue";
import BasedOnViewer from "./BasedOnViewer.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const props = withDefaults(
    defineProps<{
        works?: BasedOnWork[];
    }>(),
    {
        works: () => [],
    },
);

const emit = defineEmits<{
    (e: "onBasedOn", works: BasedOnWork[]): void;
}>();

/** Index of the work being edited; `props.works.length` while adding a new one. */
const editIndex = ref<number | null>(null);

function editedWork(index: number): BasedOnWork {
    return props.works[index] ?? { class: "SoftwareSourceCode", name: "" };
}

function onSave(work: BasedOnWork) {
    const works = [...props.works];
    works[editIndex.value!] = work;
    editIndex.value = null;
    emit("onBasedOn", works);
}

function onRemove(index: number) {
    const works = [...props.works];
    works.splice(index, 1);
    emit("onBasedOn", works);
}
</script>

<template>
    <span class="based-on-editor">
        <BasedOnForm
            v-if="editIndex !== null"
            :key="editIndex"
            :work="editedWork(editIndex)"
            @onSave="onSave"
            @onReset="editIndex = null" />
        <template v-else>
            <div v-for="(work, index) in works" :key="index">
                <BasedOnViewer :work="work">
                    <template v-slot:buttons>
                        <GButton
                            class="inline-icon-button"
                            transparent
                            icon-only
                            size="small"
                            tooltip
                            title="Edit Upstream Work"
                            @click="editIndex = index">
                            <FontAwesomeIcon :icon="faEdit" />
                        </GButton>
                        <GButton
                            class="inline-icon-button"
                            transparent
                            icon-only
                            size="small"
                            tooltip
                            title="Remove Upstream Work"
                            @click="onRemove(index)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </GButton>
                    </template>
                </BasedOnViewer>
            </div>
            <div>
                <i>
                    <a id="based-on-add" href="#" @click.prevent="editIndex = works.length"> Add an upstream work </a>
                    this workflow was adapted from.
                </i>
            </div>
        </template>
    </span>
</template>
