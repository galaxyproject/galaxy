<script setup lang="ts">
import { computed } from "vue";
import Multiselect from "vue-multiselect";

import localize from "@/utils/localization";

interface Props {
    // TODO: Replace with actual datatype type
    genomes: { id: string; text: string }[];
    databaseKeyFromElements: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    // TODO: Replace with actual datatype type
    (event: "clicked-save", attribute: string, newValue: any): void;
}>();

const selectedGenome = computed(() => props.genomes.find((element) => element.id == props.databaseKeyFromElements));

function clickedSave() {
    emit("clicked-save", "dbkey", selectedGenome.value);
}
</script>

<template>
    <div>
        <div>
            <span class="float-left h-sm">Change Database/Build of all elements in collection</span>

            <div class="text-right">
                <button
                    class="save-dbkey-edit btn btn-primary"
                    :disabled="selectedGenome?.id == databaseKeyFromElements"
                    @click="clickedSave">
                    {{ localize("Save") }}
                </button>
            </div>
        </div>

        <b>{{ localize("Database/Build") }}: </b>

        <Multiselect
            v-model="selectedGenome"
            class="database-dropdown"
            deselect-label="Can't remove this value"
            track-by="id"
            label="text"
            :options="genomes"
            :searchable="true"
            :allow-empty="false">
            {{ selectedGenome?.text }}
        </Multiselect>
    </div>
</template>
