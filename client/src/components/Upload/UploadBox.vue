<script setup>
import { ref } from "vue";

const props = defineProps({
    multiple: Boolean,
});
const isDragging = ref(false);
const emit = defineEmits();

/** Handle files dropped into the upload box **/
function onDrop(evt) {
    isDragging.value = false;
    if (evt.dataTransfer) {
        const files = evt.dataTransfer.files;
        files.forEach((file) => {
            file.chunk_mode = true;
        });
        emit("add", files);
    }
}
/*
(($) => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Handles the upload events drag/drop etc.
    /
    $.fn.uploadinput = function (options) {
        // append hidden upload field
        var $input = $(`<input type="file" style="display: none" ${(opts.multiple && "multiple") || ""}/>`);
        el.append(
            $input.change((e) => {
                opts.onchange(e.target.files);
                e.target.value = null;
            })
        );

        // exports
        return {
            dialog: () => {
                $input.trigger("click");
            },
        };
    };
})(jQuery);
*/
</script>

<template>
    <div
        class="upload-box upload-box-with-footer"
        :class="{ highlight: isDragging }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop">
        <slot />
    </div>
</template>

<style scoped>
.upload-box-with-footer {
    height: 300px;
}
</style>
