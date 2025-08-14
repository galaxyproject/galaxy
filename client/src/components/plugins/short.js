import Vue from "vue";

export default Vue.directive("short", {
    mounted(el, binding) {
        const textLength = 80;
        let textContent = binding.value;
        if (textContent.length > textLength) {
            textContent = `${textContent.substr(0, textLength)}...`;
        }
        el.classList.add("text-break");
        el.textContent = textContent;
    },
    updated(el, binding) {
        const textLength = 80;
        let textContent = binding.value;
        if (textContent.length > textLength) {
            textContent = `${textContent.substr(0, textLength)}...`;
        }
        el.classList.add("text-break");
        el.textContent = textContent;
    },
});
