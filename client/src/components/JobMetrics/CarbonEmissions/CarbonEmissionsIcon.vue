<script setup lang="ts">
import { faBolt, faCar, faGasPump, faLightbulb, faMobile, faSmog, faTree } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps<{
    icon: "bolt" | "car" | "gasPump" | "lightbulb" | "mobilePhone" | "smog" | "tree";
}>();
</script>

<template>
    <FontAwesomeIcon v-if="props.icon === 'car'" class="icon" :icon="faCar" />
    <FontAwesomeIcon v-else-if="props.icon === 'gasPump'" class="icon" :icon="faGasPump" />
    <FontAwesomeIcon v-else-if="props.icon === 'lightbulb'" class="icon" :icon="faLightbulb" />
    <FontAwesomeIcon v-else-if="props.icon === 'bolt'" class="icon" :icon="faBolt" />
    <FontAwesomeIcon v-else-if="props.icon === 'mobilePhone'" class="icon" :icon="faMobile" />
    <FontAwesomeIcon v-else-if="props.icon === 'smog'" class="icon" :icon="faSmog" />
    <FontAwesomeIcon v-else-if="props.icon === 'tree'" class="icon" :icon="faTree" />
</template>

<style scoped>
.icon {
    width: 2rem;
    height: 2rem;
}
</style>
