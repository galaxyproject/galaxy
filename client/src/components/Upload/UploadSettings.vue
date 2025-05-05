<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCog } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import UploadOption from "./UploadOption.vue";
import Popper from "@/components/Popper/Popper.vue";

library.add(faCog);

defineProps({
    deferred: {
        type: Boolean,
        default: null,
    },
    disabled: {
        type: Boolean,
        default: false,
    },
    spaceToTab: {
        type: Boolean,
        default: null,
    },
    toPosixLines: {
        type: Boolean,
        default: null,
    },
});

const emit = defineEmits(["input"]);
</script>

<template>
    <Popper placement="bottom" title="Upload Configuration" mode="primary-title" trigger="click">
        <template v-slot:reference>
            <FontAwesomeIcon class="cursor-pointer" icon="fa-cog" />
        </template>
        <div class="upload-settings-content px-2 py-2 no-highlight">
            <table class="upload-settings-table grid">
                <tbody>
                    <UploadOption
                        class="upload-space-to-tab"
                        title="Convert spaces to tabs"
                        :value="spaceToTab"
                        @click="emit('input', 'spaceToTab')" />
                    <UploadOption
                        class="upload-to-posix-lines"
                        title="Use POSIX standard"
                        :value="toPosixLines"
                        @click="emit('input', 'toPosixLines')" />
                    <UploadOption
                        v-if="deferred !== null"
                        class="upload-deferred"
                        title="Defer dataset resolution"
                        :value="deferred"
                        @click="emit('input', 'deferred')" />
                </tbody>
            </table>
            <div v-if="disabled" class="upload-settings-cover" />
        </div>
    </Popper>
</template>

<style lang="scss">
@import "theme/blue.scss";
.upload-settings-content {
    position: relative;
    .upload-settings-cover {
        background: $white;
        cursor: no-drop;
        height: 100%;
        left: 0;
        opacity: 0.25;
        position: absolute;
        top: 0;
        width: 100%;
    }
    .upload-settings-table {
        tr {
            cursor: pointer;
        }
        tr:hover {
            background-color: lighten($brand-success, 20%);
        }
    }
}
</style>
