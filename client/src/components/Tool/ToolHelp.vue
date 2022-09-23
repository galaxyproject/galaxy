<template>
    <div v-html="formatContent" class="form-help form-text mt-4"></div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";

export default {
    props: {
        content: {
            type: String,
            required: true,
        },
    },
    computed: {
        formatContent() {
            const temp = document.createElement("div");
            temp.id = "formattedContent";
            temp.insertAdjacentHTML("beforeend", this.content);
            const anchorElements = temp.getElementsByTagName("a");
            anchorElements.length > 0 ? anchorElements.forEach((elem) => elem.setAttribute("target", "_blank")) : null;
            const imageElements = temp.getElementsByTagName("img");
            imageElements.length > 0
                ? imageElements.forEach((elem) => {
                      const imgSrc = elem.getAttribute("src");
                      if (elem.src.indexOf("admin_toolshed") !== -1) {
                          elem.setAttribute("src", getAppRoot() + imgSrc);
                      }
                  })
                : null;

            return temp.innerHTML;
        },
    },
};
</script>
