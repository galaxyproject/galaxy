<script setup lang="ts">
import { ref } from "vue";

const tooltip = "Enable/Disable Help Mode";

export interface HelpModeSwitchProps {
    value: boolean;
}

const enabled = ref(false);

</script>

<template>
    <div>
        <b-form-checkbox v-model="enabled" class="no-highlight" switch :title="tooltip"> </b-form-checkbox>
    </div>
</template>
