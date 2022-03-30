import Vue from "vue";

export default Vue.directive("short", function (el, binding) {
    const textLength = 80;
    let textContent = binding.value;
    if (textContent.length > textLength) {
        textContent = `${textContent.substr(0, textLength)}...`;
    }
    el.textContent = textContent;
});
