<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faBolt,
    faCar,
    faGasPump,
    faLightbulb,
    faMobile,
    faSmog,
    faTree,
    faTruck,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faBolt, faCar, faGasPump, faLightbulb, faMobile, faSmog, faTree, faTruck);

const props = defineProps<{
    icon: "bolt" | "car" | "gasPump" | "lightbulb" | "mobilePhone" | "smog" | "tree";
}>();
</script>

<template>
    <FontAwesomeIcon v-if="props.icon === 'car'" class="icon" icon="fa-car" />
    <FontAwesomeIcon v-else-if="props.icon === 'gasPump'" class="icon" icon="fa-gas-pump" />
    <FontAwesomeIcon v-else-if="props.icon === 'lightbulb'" class="icon" icon="fa-lightbulb" />
    <FontAwesomeIcon v-else-if="props.icon === 'bolt'" class="icon" icon="fa-bolt" />
    <FontAwesomeIcon v-else-if="props.icon === 'mobilePhone'" class="icon" icon="fa-mobile" />
    <FontAwesomeIcon v-else-if="props.icon === 'smog'" class="icon" icon="fa-smog" />
    <FontAwesomeIcon v-else-if="props.icon === 'tree'" class="icon" icon="fa-tree" />
</template>

<style scoped>
.icon {
    width: 2rem;
    height: 2rem;
}
</style>
