<script setup lang="ts">
import { ref } from "vue";

import type { AgentResponse } from "./types";

import Heading from "@/components/Common/Heading.vue";

const props = defineProps<{
    metadata: NonNullable<AgentResponse["metadata"]>;
}>();

const codeToggled = ref(false);
const stdoutToggled = ref(false);
const stderrToggled = ref(false);
</script>

<template>
    <div>
        <div>
            <Heading
                h4
                size="sm"
                separator
                :collapse="codeToggled ? 'closed' : 'open'"
                @click="codeToggled = !codeToggled">
                Executed Python Code
            </Heading>
            <pre v-if="!codeToggled" class="mt-2">{{ props.metadata.executed_task?.code }}</pre>
        </div>
        <div v-if="props.metadata.stdout" class="mt-2">
            <Heading
                h4
                size="sm"
                separator
                :collapse="stdoutToggled ? 'closed' : 'open'"
                @click="stdoutToggled = !stdoutToggled">
                Execution Stdout
            </Heading>
            <pre v-if="!stdoutToggled" class="mt-2">{{ props.metadata.stdout }}</pre>
        </div>
        <div v-if="props.metadata.stderr" class="mt-2">
            <Heading
                h4
                size="sm"
                separator
                :collapse="stderrToggled ? 'closed' : 'open'"
                @click="stderrToggled = !stderrToggled">
                Execution Stderr
            </Heading>
            <pre v-if="!stderrToggled" class="mt-2 text-danger">{{ props.metadata.stderr }}</pre>
        </div>
    </div>
</template>
