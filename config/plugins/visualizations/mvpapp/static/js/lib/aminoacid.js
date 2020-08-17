// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

function AminoAcid(aaCode, aaShortName, aaName, monoMass, avgMass) {
   this.code = aaCode;
   this.shortName = aaShortName;
   this.name = aaName;
   this.mono = monoMass;
   this.avg = avgMass;
   
   this.get = _getAA;
}

AminoAcid.A = new AminoAcid ("A", "Ala", "Alanine",        71.037113805,  71.0779);
AminoAcid.R = new AminoAcid ("R", "Arg", "Arginine",      156.101111050, 156.18568);
AminoAcid.N = new AminoAcid ("N", "Asn", "Asparagine",    114.042927470, 114.10264);
AminoAcid.D = new AminoAcid ("D", "Asp", "Aspartic Acid", 115.026943065, 115.0874);
AminoAcid.C = new AminoAcid ("C", "Cys", "Cysteine",      103.009184505, 103.1429);
AminoAcid.E = new AminoAcid ("E", "Glu", "Glutamine",     129.042593135, 129.11398);
AminoAcid.Q = new AminoAcid ("Q", "Gln", "Glutamic Acid", 128.058577540, 128.12922);
AminoAcid.G = new AminoAcid ("G", "Gly", "Glycine",        57.021463735,  57.05132);
AminoAcid.H = new AminoAcid ("H", "His", "Histidine",     137.058911875, 137.13928);
AminoAcid.I = new AminoAcid ("I", "Ile", "Isoleucine",    113.084064015, 113.15764);
AminoAcid.L = new AminoAcid ("L", "Leu", "Leucine",       113.084064015, 113.15764);
AminoAcid.K = new AminoAcid ("K", "Lys", "Lysine",        128.094963050, 128.17228);
AminoAcid.M = new AminoAcid ("M", "Met", "Methionine",    131.040484645, 131.19606);
AminoAcid.F = new AminoAcid ("F", "Phe", "Phenylalanine", 147.068413945, 147.17386);
AminoAcid.P = new AminoAcid ("P", "Pro", "Proline",        97.052763875,  97.11518);
AminoAcid.S = new AminoAcid ("S", "Ser", "Serine",         87.032028435,  87.0773);
AminoAcid.T = new AminoAcid ("T", "Thr", "Threonine",     101.047678505, 101.10388);
AminoAcid.W = new AminoAcid ("W", "Trp", "Tryptophan",    186.079312980, 186.2099);
AminoAcid.Y = new AminoAcid ("Y", "Tyr", "Tyrosine",      163.063328575, 163.17326);
AminoAcid.V = new AminoAcid ("V", "Val", "Valine",         99.068413945,  99.13106);


AminoAcid.aa = [];
AminoAcid.aa["A"] = AminoAcid.A;
AminoAcid.aa["R"] = AminoAcid.R;
AminoAcid.aa["N"] = AminoAcid.N;
AminoAcid.aa["D"] = AminoAcid.D;
AminoAcid.aa["C"] = AminoAcid.C;
AminoAcid.aa["E"] = AminoAcid.E;
AminoAcid.aa["Q"] = AminoAcid.Q;
AminoAcid.aa["G"] = AminoAcid.G;
AminoAcid.aa["H"] = AminoAcid.H;
AminoAcid.aa["I"] = AminoAcid.I;
AminoAcid.aa["L"] = AminoAcid.L;
AminoAcid.aa["K"] = AminoAcid.K;
AminoAcid.aa["M"] = AminoAcid.M;
AminoAcid.aa["F"] = AminoAcid.F;
AminoAcid.aa["P"] = AminoAcid.P;
AminoAcid.aa["S"] = AminoAcid.S;
AminoAcid.aa["T"] = AminoAcid.T;
AminoAcid.aa["W"] = AminoAcid.W;
AminoAcid.aa["Y"] = AminoAcid.Y;
AminoAcid.aa["V"] = AminoAcid.V;

AminoAcid.get = _getAA;

function _getAA(aaCode) {
   if(AminoAcid.aa[aaCode])
      return AminoAcid.aa[aaCode];
   else
      return new AminoAcid(aaCode, aaCode, 0.0, 0.0);
}
