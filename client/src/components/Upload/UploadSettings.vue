<script setup>
import { computed } from "vue";
import Popper from "@/components/Popper/Popper.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";

library.add(faCog);

const props = defineProps({
    model: Object,
});
</script>

<template>
    <Popper reference-is="span" popper-is="span" placement="bottom" mode="light">
        <template v-slot:reference>
            <FontAwesomeIcon class="cursor-pointer" icon="fa-cog" />
        </template>
        <div class="p-2">Test</div>
    </Popper>
</template>
