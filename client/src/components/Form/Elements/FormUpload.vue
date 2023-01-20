<script setup>
import { ref, defineEmits } from "vue";

const props = defineProps({
    value: {
        type: Object,
    },
});

const file = ref(null);
const emit = defineEmits(["input"]);

function readFile() {
    let fileContent = file && file.value.files[0];
    var reader = new FileReader();
    if (fileContent) {
        reader.onload = () => {
            let result = reader.result
            emit(result);
            console.log("FILE CONTENTS: ", result);
        }
        reader.readAsText(fileContent);
        
        
    }
}
</script>

<template>
    <div>
        <input ref="file" type="file" @change="readFile" />
    </div>
</template>
