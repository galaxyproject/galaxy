<script setup>
import { UploadQueue } from "utils/uploadbox";

const props = defineProps({});

const emit = defineEmits();

/*
(($) => {
    // add event properties
    jQuery.event.props.push("dataTransfer");

    /**
        Handles the upload events drag/drop etc.
    /
    $.fn.uploadinput = function (options) {
        // initialize
        var el = this;
        var opts = $.extend(
            {},
            {
                ondragover: () => {},
                ondragleave: () => {},
                onchange: () => {},
                multiple: false,
            },
            options
        );

        // append hidden upload field
        var $input = $(`<input type="file" style="display: none" ${(opts.multiple && "multiple") || ""}/>`);
        el.append(
            $input.change((e) => {
                opts.onchange(e.target.files);
                e.target.value = null;
            })
        );

        // drag/drop events
        const element = el.get(0);
        element.addEventListener("drop", (e) => {
            opts.ondragleave(e);
            if (e.dataTransfer) {
                opts.onchange(e.dataTransfer.files);
                e.preventDefault();
            }
        });
        element.addEventListener("dragover", (e) => {
            e.preventDefault();
            opts.ondragover(e);
        });
        element.addEventListener("dragleave", (e) => {
            e.stopPropagation();
            opts.ondragleave(e);
        });

        // exports
        return {
            dialog: () => {
                $input.trigger("click");
            },
        };
    };
})(jQuery);

// Element
this.uploadinput = $(options.$uploadBox).uploadinput({
    multiple: this.opts.multiple,
    onchange: (files) => {
        _.each(files, (file) => {
            file.chunk_mode = true;
        });
        this.add(files);
    },
    ondragover: options.ondragover,
    ondragleave: options.ondragleave,
});
*/
</script>

<template>
    <div class="upload-box upload-box-with-footer" :class="{ highlight: true }">
        <slot />
    </div>
</template>

<style scoped>
.upload-box-with-footer {
    height: 300px;
}
</style>
