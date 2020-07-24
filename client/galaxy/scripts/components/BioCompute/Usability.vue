<template>
    <div id="usability">
        <div v-show="usability">
            <h3 class="domain">Usability Domain</h3>
            <table v-for="object in usability" :key="object">
                <tr>
                    {{
                        object
                    }}
                </tr>
                <td><button>Edit</button></td>
            </table>
        </div>
    </div>
</template>

<script>
export default {
    name: "usability",
    props: {
        usability: Array
    },
};
</script>
