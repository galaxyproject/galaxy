<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
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
import { library } from "@fortawesome/fontawesome-svg-core";

library.add(faBolt, faCar, faGasPump, faLightbulb, faMobile, faSmog, faTree, faTruck);

const props = defineProps<{
    icon: "bolt" | "car" | "gasPump" | "lightbulb" | "mobilePhone" | "smog" | "tree";
}>();
</script>

<template>
    <div v-if="props.icon === 'car'">
        <FontAwesomeIcon class="icon" icon="fa-car" />
    </div>

    <div v-else-if="props.icon === 'gasPump'">
        <FontAwesomeIcon class="icon" icon="fa-gas-pump" />
    </div>

    <div v-else-if="props.icon === 'lightbulb'">
        <FontAwesomeIcon class="icon" icon="fa-lightbulb" />
    </div>

    <div v-else-if="props.icon === 'bolt'">
        <FontAwesomeIcon class="icon" icon="fa-bolt" />
    </div>

    <div v-else-if="props.icon === 'mobilePhone'">
        <FontAwesomeIcon class="icon" icon="fa-mobile" />
    </div>

    <div v-else-if="props.icon === 'smog'">
        <FontAwesomeIcon class="icon" icon="fa-smog" />
    </div>

    <div v-else-if="props.icon === 'tree'">
        <FontAwesomeIcon class="icon" icon="fa-tree" />
    </div>
</template>

<style scoped>
.icon {
    width: 2rem;
    height: 2rem;
}
</style>
