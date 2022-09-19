<template>
    <div class="form-help form-text mt-4" v-html="formattedContent" />
</template>

<script>
import $ from "jquery";
import { getAppRoot } from "onload/loadConfig";

export default {
    props: {
        content: {
            type: String,
            required: true,
        },
    },
    computed: {
        formattedContent() {
            const $tmpl = $("<div/>").append(this.content);
            $tmpl.find("a").attr("target", "_blank");
            $tmpl.find("img").each(function () {
                const img_src = $(this).attr("src");
                if (img_src.indexOf("admin_toolshed") !== -1) {
                    $(this).attr("src", getAppRoot() + img_src);
                }
            });
            return $tmpl.html();
        },
    },
};
</script>
