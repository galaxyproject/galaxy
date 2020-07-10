// Source:  https://stackoverflow.com/questions/55910744/v-for-to-json-complex

<template>
    <table>
        <tr>
            <td>
                <h2>Object ID</h2>
            </td>
        </tr>
        <tr>
            <td>
                {{ item }}
            </td>
        </tr>
    </table>
</template>

<script>

export default {
    
    name: "tree-item",
    props: {
        item: String
    }
    
};

</script>
