<script setup>
import Popper from "@/components/Popper/Popper.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import UploadSettingsOption from "./UploadSettingsOption.vue";

library.add(faCog);

const props = defineProps({
    deferred: Boolean,
    space_to_tab: Boolean,
    to_posix_lines: Boolean,
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
                        title="Defer dataset resolution"
                        :value="deferred"
                        @click="emit('input', 'deferred')" />
                </tbody>
            </table>
        </div>
    </Popper>
</template>
