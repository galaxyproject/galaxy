<script setup lang="ts">
import { loader, useMonaco, VueMonacoEditor } from "@guolao/vue-monaco-editor";
import * as monaco from "monaco-editor";
import { nextTick, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";
import { parse, stringify } from "yaml";

import {
    type DynamicUnprivilegedToolCreatePayload,
    GalaxyApi,
    type MessageException,
    type UnprivilegedToolResponse,
} from "@/api";
import { useUnprivilegedToolStore } from "@/stores/unprivilegedToolStore";

import { setupMonaco } from "./YamlJs";

import Heading from "@/components/Common/Heading.vue";

// loaded monaco-editor from `node_modules`
loader.config({ monaco });
const { unload, monacoRef } = useMonaco();
const unprivilegedToolStore = useUnprivilegedToolStore();
const router = useRouter();

const disposeConfig = ref<() => void>();
watch(
    monacoRef,
    () => {
        if (monacoRef.value) {
            nextTick().then(() => {
                setupMonaco(monaco).then((dispose) => {
                    disposeConfig.value = dispose;
                });
            });
        }
    },
    { immediate: true },
);

onUnmounted(() => {
    disposeConfig.value!();
    unload();
});

interface ExistingTool {
    toolUuid?: string;
}
const props = defineProps<ExistingTool>();
const errorMsg = ref<MessageException>();
const persistedTool = ref<UnprivilegedToolResponse>();
const defaultYaml = `class: GalaxyUserTool
id:
name:
version: "0.1"
description:
container:
shell_command:
inputs:
  - name: input1
    type: data
outputs:
  - name: output1
    type: data`;
const yamlRepresentation = ref<string>(defaultYaml);

if (props.toolUuid) {
    GalaxyApi()
        .GET("/api/unprivileged_tools/{uuid}", {
            params: {
                path: {
                    uuid: props.toolUuid,
                },
            },
        })
        .then(({ data, error }) => {
            if (!error) {
                yamlRepresentation.value = stringify(data.representation, {
                    blockQuote: "literal",
                });
            }
        });
}

async function saveTool() {
    if (!yamlRepresentation.value) {
        console.error("No yaml to parse");
        return;
    }
    const payload: DynamicUnprivilegedToolCreatePayload = {
        active: true,
        hidden: false,
        representation: parse(yamlRepresentation.value),
        src: "representation",
    };
    const { data, error } = await GalaxyApi().POST("/api/unprivileged_tools", { body: payload });
    if (error) {
        errorMsg.value = error;
    } else {
        persistedTool.value = data;
        unprivilegedToolStore.load(true);
        router.push(`/tools/editor/${data.uuid}`);
    }
}
</script>

<template>
    <div>
        <div class="d-flex flex-gapx-1">
            <Heading h1 separator inline size="lg" class="flex-grow-1 mb-2">Tool Editor</Heading>
            <b-button variant="primary" size="m" @click="saveTool">Save</b-button>
        </div>
        <VueMonacoEditor
            v-model="yamlRepresentation"
            language="yaml-with-js"
            default-path="tool.yml"
            :options="{
                quickSuggestions: {
                    other: true,
                    comments: false,
                    strings: true,
                },
            }">
        </VueMonacoEditor>
    </div>
</template>
