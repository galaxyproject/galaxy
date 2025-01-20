<script setup lang="ts">
import { faExclamation } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";

const props = defineProps<{
    alerts: string[];
    hasAlertClass?: boolean;
}>();
</script>

<template>
    <component :is="props.hasAlertClass ? BAlert : 'span'" show variant="info">
        <div v-for="(alert, index) in props.alerts" :key="index" class="ui-form-error">
            <FontAwesomeIcon class="mr-1" :icon="faExclamation" />
            <!-- eslint-disable-next-line vue/no-v-html -->
            <span class="ui-form-error-text" v-html="alert" />
        </div>
    </component>
</template>
