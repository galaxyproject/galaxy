<script setup lang="ts">
import { loader, useMonaco, VueMonacoEditor } from "@guolao/vue-monaco-editor";
import * as monaco from "monaco-editor";
import { onUnmounted, ref } from "vue";
import { parse, stringify } from "yaml";

import {
    type DynamicUnprivilegedToolCreatePayload,
    GalaxyApi,
    type MessageException,
    type UnprivilegedToolResponse,
} from "@/api";

import { setupEditor, setupMonaco } from "./YamlJs";

import Heading from "@/components/Common/Heading.vue";

// loaded monaco-editor from `node_modules`
loader.config({ monaco });
const { unload, monacoRef } = useMonaco();

const disposeConfig = ref<() => void>();
const { dispose, providerFunctions } = setupMonaco(monaco);
disposeConfig.value = dispose;

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
description:
container:
shell_command:
inputs:
outputs:`;
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
                yamlRepresentation.value = stringify(data.representation);
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
        allow_load: true,
    };
    const { data, error } = await GalaxyApi().POST("/api/unprivileged_tools", { body: payload });
    if (error) {
        errorMsg.value = error;
    } else {
        persistedTool.value = data;
    }
}

async function setupEditorWrapper() {
    if (monacoRef.value) {
        setupEditor(providerFunctions);
    }
}
</script>

<template>
    <div>
        <div class="d-flex flex-gapx-1">
            <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Tool Editor</Heading>
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
            }"
            @mount="setupEditorWrapper">
        </VueMonacoEditor>
    </div>
</template>
