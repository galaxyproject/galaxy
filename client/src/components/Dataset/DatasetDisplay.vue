<script setup lang="ts">
import axios from "axios";
import { onMounted, ref } from "vue";
import { withPrefix } from "@/utils/redirect";

interface Props {
    datasetId: string;
    isPreview: boolean;
}

const props = withDefaults(defineProps<Props>(), {});

const content = ref();

onMounted(async () => {
    const url = withPrefix(`/datasets/${props.datasetId}/display/?preview=True`);
    try {
        const { data } = await axios.get(url);
        content.value = data;
    } catch (e) {
        console.error(e);
    }

});
</script>

<template>
    <pre>
        {{  content }}
    </pre>
</template>

