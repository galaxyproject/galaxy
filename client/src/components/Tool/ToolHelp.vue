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
            let temp = document.createElement("div")
            temp.id = 'formattedContent'
            temp.insertAdjacentHTML( 'beforeend', this.content );
            temp.getElementsByTagName('a').forEach(elem => elem.setAttribute('target', '_blank'))
            temp.getElementsByTagName('img').forEach((elem) => {
                const imgSrc = elem.getAttribute("src")
                if(elem.src.indexOf('admin_toolshed') !== -1) {
                    elem.setAttribute('src', getAppRoot() + imgSrc)
                }
            })
            return temp.innerHTML
        }
    }
};
</script>
