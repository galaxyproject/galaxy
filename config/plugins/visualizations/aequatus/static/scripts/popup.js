/**
 * Created with IntelliJ IDEA.
 * User: thankia
 * Date: 28/11/14
 * Time: 15:13
 * To change this template use File | Settings | File Templates.
 */

var mouseX, mouseY;

function newpopup(member_id, protein_id) {


var gene;
    var stable_id;

    jQuery('#stable_label').html("")


    jQuery('#makemetop_button').html("")

    jQuery('#ref_name').html("")

    jQuery('#position').html("")

    jQuery('#disp_label').html("")

    jQuery('#gene_desc').html("")

    jQuery('#ensemblLink').html("")

    jQuery('#ensemblLink').html("<a href='http://www.ensembl.org/id/" + stable_id + "'>Link to Ensembl</a>")

    jQuery("#popup").css({"left": mouseX - jQuery("#popup").width() - 5});
    jQuery("#popup").css({"top": (mouseY - jQuery("#popup").height() - 30)});


    jQuery("#popup").fadeIn();




    gene = syntenic_data.member[member_id];
    stable_id = syntenic_data.member[member_id].id

    if(gene.display_name){
        jQuery('#name_label').html(gene.display_label)
    }else if(gene.description){
        jQuery('#name_label').html(gene.description)
    }else {
        jQuery('#name_label').html(stable_id)
    }

    var desc = gene.desc

    jQuery('#makemetop_button').html("<button onclick='changeReference(\"" + member_id + "\",\""+protein_id+"\")' class='btn btn-default' type='button'> <i class='fas fa-random fa-1x'></i></button>");

    jQuery('#ref_name').html("Chr " + gene.seq_region_name)

    jQuery('#position').html(gene.start + " - " + gene.end)

    jQuery('#gene_desc').html(stringTrim(gene.description, 200))

    jQuery('#ensemblLink').html("<a target='_blank' href='http://www.ensembl.org/Multi/Search/Results?q=" + stable_id + "'><button type='button' class='btn btn-default'> <i class='fas fa-1x'>e!</i></button></a>")


}

function removePopup() {
    jQuery("#popup").fadeOut()
}
