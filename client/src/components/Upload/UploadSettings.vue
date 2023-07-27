<script setup>
import Popper from "@/components/Popper/Popper.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { faCheckSquare } from "@fortawesome/free-solid-svg-icons";
import { faSquare } from "@fortawesome/free-regular-svg-icons";

library.add(faCheckSquare, faCog, faSquare);

const props = defineProps({
    model: Object,
});

const availableSettings = [
    {
        id: "space_to_tab",
        title: "Convert spaces to tabs",
    },
    {
        id: "to_posix_lines",
        title: "Use POSIX standard",
    },
    {
        id: "deferred",
        title: "Defer dataset resolution",
    },
];
</script>

<template>
    <Popper placement="bottom" title="Upload Configuration" mode="primary-title" trigger="click-to-open">
        <template v-slot:reference>
            <FontAwesomeIcon class="cursor-pointer" icon="fa-cog" />
        </template>
        <div class="upload-settings px-2 py-2">
            <table class="upload-settings-table grid">
                <tbody>
                    <tr v-for="setting in availableSettings" :key="setting.id">
                        <td>
                            <FontAwesomeIcon v-if="model['setting.id']" icon="fas fa-check-square" fa-fw />
                            <FontAwesomeIcon v-else icon="far fa-square" fa-fw />
                        </td>
                        <td>{{ setting.title }}</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </Popper>
</template>
