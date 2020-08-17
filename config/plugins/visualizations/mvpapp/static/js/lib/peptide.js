// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

// -----------------------------------------------------------------------------
// Peptide sequence and modifications
// -----------------------------------------------------------------------------
function Peptide(seq, staticModifications, varModifications, ntermModification, ctermModification) {
	
	var sequence = seq;
	var ntermMod = ntermModification;
	var ctermMod = ctermModification;
	var staticMods = [];
	if(staticModifications) {
		for(var i = 0; i < staticModifications.length; i += 1) {
			var mod = staticModifications[i];
			staticMods[mod.aa.code] = mod;
		}
	}
	
	var varMods = [];
	if(varModifications) {
		for(var i = 0; i < varModifications.length; i += 1) {
			var mod = varModifications[i];
			varMods[mod.position] = mod;
		}
	}

    this.sequence = function () {
        return sequence;
    }

    this.varMods = function() {
        return varMods;
    }

    this.staticMods = function() {
        return staticMods;
    }

    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMassMono = function _seqMassMono(index, term) {
        return _getSeqMass(null, index, term, "mono");
    }


    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMassAvg = function _seqMassAvg(index, term) {
        return _getSeqMass(null, index, term, "avg");
    }

    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMass = _getSeqMass;



    // Returns the monoisotopic neutral mass of the peptide; modifications added. N-term H and C-term OH are added
    this.getNeutralMassMono = function _massNeutralMono() {

        var mass = 0;
        var aa_obj = new AminoAcid();
        if(sequence) {
            for(var i = 0; i < sequence.length; i++) {
                var aa = aa_obj.get(sequence.charAt(i));
                mass += aa.mono;
            }
        }

        mass = _addTerminalModMass(mass, "n");
        mass = _addTerminalModMass(mass, "c");
        mass = _addResidueModMasses(mass, sequence.length, "n");
        // add N-terminal H
        mass = mass + Ion.MASS_H_1;
        // add C-terminal OH
        mass = mass + Ion.MASS_O_16 + Ion.MASS_H_1;

        return mass;
    }

    //Returns the avg neutral mass of the peptide; modifications added. N-term H and C-term OH are added
    this.getNeutralMassAvg = function _massNeutralAvg() {

        var mass = 0;
        var aa_obj = new AminoAcid();
        if(sequence) {
            for(var i = 0; i < sequence.length; i++) {
                var aa = aa_obj.get(sequence.charAt(i));
                mass += aa.avg;
            }
        }

        mass = _addTerminalModMass(mass, "n");
        mass = _addTerminalModMass(mass, "c");
        mass = _addResidueModMasses(mass, sequence.length, "n");
        // add N-terminal H
        mass = mass + Ion.MASS_H;
        // add C-terminal OH
        mass = mass + Ion.MASS_O + Ion.MASS_H;

        return mass;
    }

    function _addResidueModMasses(seqMass, slice, term) {

        var mass = seqMass;
        if(typeof(slice) == "number")
            slice = new _Slice(null, slice, term);
        for( var i = slice.from; i < slice.to; i += 1) {
            // add any static modifications
            var mod = staticMods[sequence.charAt(i)];
            if(mod) {
                mass += mod.modMass;
            }
            // add any variable modifications
            mod = varMods[i+1]; // varMods index in the sequence is 1-based
            if(mod) {
                mass += mod.modMass;
            }
        }

        return mass;
    }

    this.getSubSequence = function _getSubSeq(endIndex, term) {
        var slice = new _Slice(null, endIndex, term);
        var subSequence = ''
        if(sequence) {
            for( var i = slice.from; i < slice.to; i += 1) {
                subSequence += sequence[i];
            }
        }
        return subSequence;
    }

    function _getSeqMass(startIndex, endIndex, term, massType) {

        var mass = 0;
        var aa_obj = new AminoAcid();
        var slice = new _Slice(startIndex, endIndex, term);
        if(sequence) {
            for( var i = slice.from; i < slice.to; i += 1) {
                var aa = aa_obj.get(sequence[i]);
                mass += aa[massType];
            }
        }
        if(startIndex == null)
            mass = _addTerminalModMass(mass, term);
        mass = _addResidueModMasses(mass, slice, term);
        return mass;
    }


    function _addTerminalModMass(seqMass, term) {

        var mass = seqMass;
        // add any terminal modifications
        if(term == "n" && ntermMod)
            mass += ntermMod;
        if(term == "c" && ctermMod)
            mass += ctermMod;

        return mass;
    }

    // Defines a range or subsequence of peptide to iterate over.
    // If term is "n", than the range is from startIndex (or 0 if 
    // startIndex is null) to endIndex. If term is "c", the range is 
    // from endIndex to startIndex (or sequence.length if startIndex
    // is null).
    function _Slice(startIndex, endIndex, term) {
        if(term == "n") {
            // If N-term sense, start from begining 
            this.from = startIndex == null ? 0 : startIndex;
            this.to = endIndex;
        }
        if(term == "c") {
            this.from = endIndex;
            this.to = startIndex == null ? sequence.length : startIndex;
        }
    }
}


//-----------------------------------------------------------------------------
// Modification
//-----------------------------------------------------------------------------
function Modification(aminoAcid, mass) {
	this.aa = aminoAcid;
	this.modMass = mass;
}

function VariableModification(pos, mass, aminoAcid) {
	this.position = parseInt(pos);
	this.aa = aminoAcid;
	this.modMass = mass;
}



