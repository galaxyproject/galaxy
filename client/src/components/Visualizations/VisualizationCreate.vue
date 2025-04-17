<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { debounce } from "lodash";
import { computed, onMounted, ref } from "vue";

import { getAppRoot } from "@/onload/loadConfig";

const props = withDefaults(
    defineProps<{
        visualization: string;
    }>(),
    {
    }
);

const emit = defineEmits(["change"]);

const errorMessage = ref("");

</script>

<template>
    <div v-if="errorMessage">
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
    </div>
    <div v-else>
        {{ visualization }}
    </div>
</template>
