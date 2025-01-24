import { defineStore } from "pinia";
import { ref } from "vue";

export const useUploadStore = defineStore("upload", () => {
    const percentage = ref<number>(0);
    const status = ref<string>("");

    return { percentage, status };
});
