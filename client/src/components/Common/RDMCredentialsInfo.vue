<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { RouterLink } from "vue-router";

interface Props {
    selectedRepository?: string;
}

withDefaults(defineProps<Props>(), {
    selectedRepository: "the selected repository",
});
</script>

<template>
    <BAlert show variant="info">
        You may need to setup your credentials for {{ selectedRepository }} in your
        <RouterLink to="/user/information" target="_blank">preferences page</RouterLink> to be able to export. You can
        also define some default options for the export in those settings, like the public name you want to associate
        with your records.
    </BAlert>
</template>
