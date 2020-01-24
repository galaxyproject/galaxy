/**
 * This function chekcs visual settings before drawing genes and tree
 */
function checkVisuals() {

    if (jQuery("#deleteCheck").is(':checked'))
        jQuery(".delete").show();  // checked
    else
        jQuery(".delete").hide();  // unchecked

    if (jQuery("#matchCheck").is(':checked'))
        jQuery(".match").show();  // checked
    else
        jQuery(".match").hide();  // unchecked

    if (jQuery("#insertCheck").is(':checked'))
        jQuery(".insert").show();  // checked
    else
        jQuery(".insert").hide();  // unchecked

    if (jQuery("#utrCheck").is(':checked'))
        jQuery(".utr").show();  // checked
    else
        jQuery(".utr").hide();  // unchecked jQuery('.utr').toggle()

    if (jQuery('input[name=label_type]:radio:checked').val() == "gene_stable") {
        changeToStable()
    } else if (jQuery('input[name=label_type]:radio:checked').val() == "ptn_stable") {
        changeToProteinId()
    } else {
        changeToGeneInfo()
    }

    if (jQuery('input[name=view_type]:checked').val() == "with") {
        changeToExon();
    }
    else {
        changeToNormal();
    }
}

function stringTrim(string, width, newClass) {
    if (newClass) {
        jQuery("#ruler").addClass(newClass.toString())
    }
    else {
        jQuery("#ruler").addClass("ruler")
    }

    var ruler = jQuery("#ruler");
    var inLength = 0;
    var tempStr = "";

    jQuery("#ruler").html(string);
    inLength = jQuery("#ruler").width();

    if (newClass) {
        jQuery("#ruler").removeClass(newClass.toString())
    }
    else {
        jQuery("#ruler").removeClass("ruler")
    }

    if (inLength < width) {
        return string;
    }
    else {
        width = parseInt(string.length * width / inLength);
        var string_title = string.replace(/\s+/g, '&nbsp;');
        return "<span title=" + string_title + ">" + string.substring(0, width) + "... </span>";
    }

}
