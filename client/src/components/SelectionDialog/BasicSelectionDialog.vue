<script setup lang="ts">
import type { IconDefinition } from "font-awesome-6";
import { computed, onMounted, type Ref, ref } from "vue";

import { type SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import { errorMessageAsString } from "@/utils/simple-error";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

interface Props {
    detailsKey?: string;
    getData: () => Promise<object[]>;
    isEncoded?: boolean;
    labelKey?: string;
    leafIcon?: IconDefinition | null;
    timeKey?: string;
    title: string;
}

const props = withDefaults(defineProps<Props>(), {
    detailsKey: "",
    isEncoded: false,
    labelKey: "id",
    leafIcon: null,
    timeKey: "update_time",
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onOk", results: SelectionItem): void;
    (e: "onUpload"): void;
}>();

const errorMessage = ref("");
const items: Ref<Array<SelectionItem>> = ref([]);
const modalShow = ref(true);
const optionsShow = ref(false);
const showTime = ref(false);

const fields = computed(() => {
    const fields = [{ key: "label" }];
    if (props.detailsKey) {
        fields.push({ key: "details" });
    }
    if (showTime.value) {
        fields.push({ key: "time" });
    }
    return fields;
});

async function load() {
    optionsShow.value = false;
    try {
        // TODO: Consider supporting pagination here
        // this could potentially load quite a lot of items
        const incoming = await props.getData();
        items.value = incoming.map((item: any) => {
            const timeStamp = item[props.timeKey];
            showTime.value = !!timeStamp;
            return {
                id: item.id,
                label: item[props.labelKey] || null,
                details: item[props.detailsKey] || null,
                time: timeStamp || null,
                isLeaf: true,
                url: "",
            };
        });
        optionsShow.value = true;
    } catch (err) {
        errorMessage.value = errorMessageAsString(err);
    }
}

onMounted(() => load());
</script>

<template>
    <SelectionDialog
        :error-message="errorMessage"
        :fields="fields"
        :options-show="optionsShow"
        :modal-show="modalShow"
        :is-encoded="isEncoded"
        :leaf-icon="leafIcon"
        :items="items"
        :title="title"
        @onCancel="emit('onCancel')"
        @onClick="emit('onOk', $event)" />
</template>
