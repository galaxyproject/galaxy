<template>
    <BAlert v-if="errorMessage" variant="warning" show>{{ errorMessage }}</BAlert>
    <div v-else class="p-2">
        <ConfigureHeader :has-changed="hasChanged" @ok="onOk" @cancel="$emit('cancel')" />
        <div v-if="urlReferences.length > 0">
            <div v-for="(ref, index) in urlReferences" :key="index">
                <ConfigureSelector
                    :object-name="getDisplayLabel(ref.value)"
                    :object-title="formatKeyPath(ref.keyPath)"
                    object-type="history_dataset_id"
                    @change="onChange(ref.keyPath, $event)" />
            </div>
        </div>
        <BAlert v-else variant="warning" show>No URL-like fields found.</BAlert>
        <FormElementLabel title="Height" help="Specify the height of the view in pixels.">
            <FormNumber id="vitessce-height" v-model="height" :min="100" :max="1000" type="integer" @input="onHeight" />
        </FormElementLabel>
    </div>
</template>

<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { type Ref, ref, watch } from "vue";

import { stringify } from "@/components/Markdown/Utilities/stringify";
import type { OptionType } from "@/components/SelectionField/types";
import { getAppRoot } from "@/onload";

import ConfigureHeader from "./ConfigureHeader.vue";
import ConfigureSelector from "./ConfigureSelector.vue";
import FormNumber from "@/components/Form/Elements/FormNumber.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";

interface VitessceType {
    __gx_height?: number;
    [key: string]: unknown;
}

const DEFAULT_HEIGHT = 400;

const props = defineProps<{
    name: string;
    content: string;
}>();

const emit = defineEmits<{
    (e: "cancel"): void;
    (e: "change", content: string): void;
}>();

const contentObject: Ref<VitessceType> = ref({});
const errorMessage = ref();
const hasChanged = ref(false);
const height = ref();
const urlReferences: Ref<UrlReference[]> = ref([]);

const urlRegex = /^[a-zA-Z][a-zA-Z0-9+.-]*:\/\/[^\s]+$/;

interface UrlReference {
    keyPath: (string | number)[];
    value: string;
}

function isUrl(value: unknown): value is string {
    return typeof value === "string" && urlRegex.test(value);
}

function findAllUrlFields(obj: unknown, path: (string | number)[] = []): UrlReference[] {
    const results: UrlReference[] = [];
    if (Array.isArray(obj)) {
        obj.forEach((item, index) => {
            results.push(...findAllUrlFields(item, [...path, index]));
        });
    } else if (typeof obj === "object" && obj !== null) {
        for (const [key, value] of Object.entries(obj)) {
            if (isUrl(value)) {
                results.push({ keyPath: [...path, key], value });
            }
            results.push(...findAllUrlFields(value, [...path, key]));
        }
    }
    return results;
}

function onChange(keyPath: (string | number)[], option: OptionType) {
    const parentPath = keyPath.slice(0, -1);
    const urlKey = keyPath[keyPath.length - 1];
    const parent = parentPath.reduce((acc: any, key) => acc?.[key], contentObject.value);
    if (parent && (typeof urlKey === "string" || typeof urlKey === "number")) {
        const target = parent as Record<string | number, any>;
        target[urlKey] = `${window.location.origin}${getAppRoot()}api/datasets/${option.id}/display`;
        hasChanged.value = true;
        urlReferences.value = findAllUrlFields(contentObject.value);
    }
}

function formatKeyPath(keyPath: (string | number)[]): string {
    return keyPath
        .map((key) => {
            if (typeof key === "number" || /^\d+$/.test(String(key))) {
                return ` ${Number(key) + 1}`;
            } else {
                const part = String(key);
                return part.charAt(0).toUpperCase() + part.slice(1);
            }
        })
        .reduce((acc, part, idx, arr) => {
            if (idx > 0 && /^\s\d+$/.test(part)) {
                return acc.slice(0, -1).concat(`${acc[acc.length - 1]}${part}`);
            }
            return acc.concat(part);
        }, [] as string[])
        .join(" > ");
}

function getDisplayLabel(value: string): string {
    if (value.startsWith("galaxy://")) {
        const query = value.replace("galaxy://", "");
        const params = Object.fromEntries(new URLSearchParams(query));
        return params.dataset_name || params.dataset_label || value;
    }
    return value;
}

function onHeight(newHeight: number) {
    contentObject.value.__gx_height = newHeight;
    hasChanged.value = true;
}

function onOk() {
    emit("change", stringify(contentObject.value));
}

function parseContent() {
    try {
        contentObject.value = JSON.parse(props.content);
        height.value = contentObject.value.__gx_height || DEFAULT_HEIGHT;
        urlReferences.value = findAllUrlFields(contentObject.value);
        errorMessage.value = "";
    } catch (e) {
        errorMessage.value = `Failed to parse: ${e}`;
    }
}

watch(
    () => props.content,
    () => parseContent(),
    { immediate: true }
);
</script>
