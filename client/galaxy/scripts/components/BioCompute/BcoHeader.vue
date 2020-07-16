<template>
    <table>
        <tr>
            <td>
                <h2>Object ID</h2>
            </td>
            <td>
            </td>
                <h2>e-Tag</h2>
            <td>
                <h2>Spec Version</h2>
            </td>
        </tr>
        <tr>
            <td class='bold_except'>
                {{ objectid }}
            </td>
            <td>
            </td>
            <td>
                {{ etag }}
            </td>
            <td>
            </td>
            <td>
                {{ specversion }}
            </td>
        </tr>
    </table>
</template>

<script>

export default {

    props: {
        objectid: String,
        etag: String,
        specversion: String
    }
    
};

</script>
