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
export default {
    name: "tree-item",
    props: {
        item: Object
    },
    methods: {

        // Parse the names.
        parse_names: function(incoming) {

            // Is incoming a string?
            if (typeof(incoming) === 'string') {

                // Does the name match the dash pattern?
                if (incoming.search("((.*?)_)*") != -1) {

                    // Found a match, so split and capitalize.
                    var split_up = incoming.split('_');
                    
                    // Source:  https://stackoverflow.com/questions/1026069/how-do-i-make-the-first-letter-of-a-string-uppercase-in-javascript

                    var new_array = split_up.map(function(e) {
                        return e.charAt(0).toUpperCase() + e.slice(1);
                    });
                    
                    // Re-join.
                    incoming = new_array.join(' ');

                }

            }
            
            return (incoming)

        }

    }
};
</script>
