<script setup lang="ts">
import { onMounted, ref } from "vue";
import Multiselect from "vue-multiselect";

import localize from "@/utils/localization";

interface Props {
    genomes: { id: string; text: string }[];
    databaseKeyFromElements: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (event: "clicked-save", attribute: string, newValue: any): void;
}>();

const selectedGenome = ref();

function clickedSave() {
    emit("clicked-save", "dbkey", selectedGenome.value);
}

onMounted(() => {
    selectedGenome.value = props.genomes.find((element) => element.id == props.databaseKeyFromElements);
});
</script>

<template>
    <div>
        <div>
            <span class="float-left h-sm">更改集合中所有元素的数据库/构建</span>

            <div class="text-right">
                <button
                    class="save-dbkey-edit btn btn-primary"
                    :disabled="selectedGenome?.id == databaseKeyFromElements"
                    @click="clickedSave">
                    {{ localize("保存") }}
                </button>
            </div>
        </div>

        <b>{{ localize("数据库/构建") }}: </b>

        <Multiselect
            v-model="selectedGenome"
            class="database-dropdown"
            deselect-label="无法移除此值"
            track-by="id"
            label="text"
            :options="genomes"
            :searchable="true"
            :allow-empty="false">
            {{ selectedGenome?.text }}
        </Multiselect>
    </div>
</template>