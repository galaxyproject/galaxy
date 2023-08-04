<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import UploadSettingsOption from "./UploadSettingsOption.vue";
import Popper from "@/components/Popper/Popper.vue";

library.add(faCog);

const props = defineProps({
    deferred: {
        type: Boolean,
        default: null,
    },
    space_to_tab: {
        type: Boolean,
        default: null,
    },
    to_posix_lines: {
        type: Boolean,
        default: null,
    },
});

const emit = defineEmits();
</script>

<template>
    <Popper placement="bottom" title="Upload Configuration" mode="primary-title" trigger="click-to-open">
        <template v-slot:reference>
            <FontAwesomeIcon class="cursor-pointer" icon="fa-cog" />
        </template>
        <div class="upload-settings px-2 py-2">
            <table class="upload-settings-table grid">
                <tbody>
                    <UploadSettingsOption
                        title="Convert spaces to tabs"
                        :value="space_to_tab"
                        @click="emit('input', 'space_to_tab')" />
                    <UploadSettingsOption
                        title="Use POSIX standard"
                        :value="to_posix_lines"
                        @click="emit('input', 'to_posix_lines')" />
                    <UploadSettingsOption
                        v-if="deferred !== null"
                        title="Defer dataset resolution"
                        :value="deferred"
                        @click="emit('input', 'deferred')" />
                </tbody>
            </table>
        </div>
    </Popper>
</template>
