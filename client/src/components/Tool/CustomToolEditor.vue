<script setup lang="ts">
import { faArrowAltCircleUp, faLightbulb, faSave } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { loader, useMonaco, VueMonacoEditor } from "@guolao/vue-monaco-editor";
import * as monaco from "monaco-editor";
// Import workers using Vite's ?worker syntax for proper bundling
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";
import yamlWorker from "monaco-yaml/yaml.worker?worker";
import { nextTick, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
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

// Configure Monaco environment with worker factory before loading
self.MonacoEnvironment = {
    getWorker(_workerId: string, label: string) {
        if (label === "yaml") {
            return new yamlWorker();
        }
        if (label === "json") {
            return new jsonWorker();
        }
        if (label === "typescript" || label === "javascript") {
            return new tsWorker();
        }
        return new editorWorker();
    },
};

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

async function importFromUrl() {
    const url = prompt("Enter the URL to import YAML from:");
    if (!url) {
        return;
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error("Failed to fetch YAML");
        }

        const yaml = await response.text();
        yamlRepresentation.value = yaml;
    } catch (error) {
        errorMsg.value = { err_code: -1, err_msg: `Couldn't import YAML from URL: ${error}` };
    }
}

const generating = ref(false);

async function generateViaLLM() {
    const userPrompt = prompt("Describe the tool you would like to build");
    if (!userPrompt) {
        return;
    }

    generating.value = true;
    errorMsg.value = undefined;

    try {
        const response = await GalaxyApi().POST("/api/ai/agents/custom-tool", {
            body: { query: userPrompt },
        });

        if (response.error) {
            errorMsg.value = { err_code: response.error.err_code, err_msg: response.error.err_msg };
            return;
        }

        // Check if the response contains tool YAML in metadata
        const metadata = response.data?.metadata as { tool_yaml?: string; error?: string } | undefined;
        const toolYaml = metadata?.tool_yaml;
        if (toolYaml) {
            yamlRepresentation.value = toolYaml;
        } else if (metadata?.error === "model_capability") {
            // Model doesn't support structured output
            errorMsg.value = {
                err_code: -1,
                err_msg:
                    "The configured AI model doesn't support tool generation. Please contact your administrator to configure a compatible model.",
            };
        } else {
            const content = response.data?.content as string | undefined;
            errorMsg.value = {
                err_code: -1,
                err_msg: content ?? "Failed to generate tool definition",
            };
        }
    } catch (error) {
        errorMsg.value = { err_code: -1, err_msg: `Couldn't generate YAML: ${error}` };
    } finally {
        generating.value = false;
    }
}
</script>

<template>
    <div>
        <b-alert v-if="errorMsg" variant="danger" show dismissible>
            {{ errorMsg.err_msg }}
        </b-alert>
        <div class="d-flex flex-gapx-1">
            <Heading h1 separator inline size="lg" class="flex-grow-1 mb-2">Tool Editor</Heading>
            <b-button
                variant="secondary"
                size="m"
                title="Generate via AI"
                data-description="Generate via AI"
                :disabled="generating"
                @click="generateViaLLM"
                ><FontAwesomeIcon :icon="faLightbulb"
            /></b-button>
            <b-button
                variant="secondary"
                size="m"
                title="Import from URL"
                data-description="Import from a URL"
                @click="importFromUrl"
                ><FontAwesomeIcon :icon="faArrowAltCircleUp"
            /></b-button>
            <b-button
                variant="primary"
                size="m"
                title="Save Custom Tool"
                data-description="save custom tool"
                @click="saveTool"
                ><FontAwesomeIcon :icon="faSave"
            /></b-button>
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
