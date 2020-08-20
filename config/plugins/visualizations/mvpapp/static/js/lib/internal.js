// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

INTERNAL_ION_COLOR = "#C71585";

function InternalIon(peptide, start, end, massType, minus28) {
    var sequence = "";
    for(var i = start; i < end; i++) {
        var aa = peptide.sequence().charAt(i);
        var staticMod = peptide.staticMods()[aa];
        var variableMod = peptide.varMods()[i];
        var mod = (staticMod ? staticMod.modMass : 0) + (variableMod ? variableMod.modMass : 0);
        sequence += aa + (mod != 0 ? ("(" + mod + ")") : "");
    }
    this.sequence = sequence;
    this.subSequence = sequence;
    this.label = "<" + sequence + ">" + (minus28 ? "-CO" : ""); 
    // TODO: Verify calculation, depends on massType?   
    var massAdjust = Ion.MASS_PROTON;
    if(minus28) {
        massAdjust -= massType == "mono" ? Ion.MASS_C_12 : Ion.MASS_C;
        massAdjust -= massType == "mono" ? Ion.MASS_O_16 : Ion.MASS_O;
    }
    this.mz = peptide.getSeqMass(start, end, "n", massType) + massAdjust;
    this.massType = massType;
    this.charge = 1;
    this.internal = true;
    this.minus28 = minus28 ? true : false;
}

var getInternalIons = function(peptide, massType) {
    var seqLength = peptide.sequence().length;
    var labels = [];
    var interalIons = [];
    for(var i = 1; i < seqLength - 1; i++) {
        for(var j = i + 2; j < seqLength; j++) {
            var internalIon = new InternalIon(peptide, i, j, massType, false);
            var label = internalIon.label;
            if(!labels[label]) {
                labels[label] = true;
                interalIons.push(internalIon);
            }
            internalIon = new InternalIon(peptide, i, j, massType, true);
            label = internalIon.label;
            if(!labels[label]) {
                labels[label] = true;
                interalIons.push(internalIon);
            }
        }
    }
    sortByMz(interalIons);
    return interalIons;
}

var sortByMz = function(ionArray) {
    ionArray.sort(function(ion1, ion2) { return ion1.mz - ion2.mz;})
}