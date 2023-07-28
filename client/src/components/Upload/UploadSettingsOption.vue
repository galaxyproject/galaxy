<script setup>
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare } from "@fortawesome/free-solid-svg-icons";
import { faSquare } from "@fortawesome/free-regular-svg-icons";

library.add(faCheckSquare, faSquare);

const props = defineProps({
    id: String,
    title: String,
    value: Boolean,
});

const emit = defineEmits();
</script>

<template>
    <tr @click="emit('click')">
        <td>
            <FontAwesomeIcon class="px-2" v-if="value" icon="fas fa-check-square" fa-fw />
            <FontAwesomeIcon class="px-2" v-else icon="far fa-square" fa-fw />
        </td>
        <td class="text-left">
            <span class="pr-2">{{ title }}</span>
        </td>
    </tr>
</template>
