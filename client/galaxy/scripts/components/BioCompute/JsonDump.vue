// Source:  https://stackoverflow.com/questions/55910744/v-for-to-json-complex

<template>
    <li>
        {{ parse_names(item.name) }}
        <ul>
            <tree-item
                class="item"
                v-for="(child, index) in item.children"
                :key="index"
                :item="child"
                >
            </tree-item>
        </ul>
    </li>
</template>

<script>

// Imports
import parseFields from './scripts/parseFields';

export default {

    name: "tree-item",
    created() {
    	this.parse_names = parseFields.parse_names;
    },
    props: {
        item: Object
    }
    
};

</script>
