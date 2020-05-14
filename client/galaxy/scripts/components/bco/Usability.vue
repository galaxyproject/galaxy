<template>
    <div id="usability">
        <div v-show="bco">
            <h2 class="domain">Usability Domain</h2>
            <table v-for="object in bco.usability_domain" :key="object">
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
    props: ["bco"],
};
</script>
