Clazz.declarePackage("J.adapter.readers.cif");
Clazz.load(["J.adapter.readers.cif.MMCifReader"], "J.adapter.readers.cif.BCIFReader", ["JU.MessagePackReader", "J.adapter.readers.cif.BCIFDataParser", "$.BCIFDecoder", "$.CifReader"], function(){
var c$ = Clazz.decorateAsClass(function(){
this.bcifParser = null;
this.version = null;
this.catName = null;
this.colCount = 0;
Clazz.instantialize(this, arguments);}, J.adapter.readers.cif, "BCIFReader", J.adapter.readers.cif.MMCifReader);
Clazz.overrideMethod(c$, "getCifDataParser", 
function(){
return this.cifParser = this.bcifParser =  new J.adapter.readers.cif.BCIFDataParser(this, this.debugging);
});
Clazz.overrideMethod(c$, "setup", 
function(fullPath, htParams, reader){
this.isBinary = true;
this.setupASCR(fullPath, htParams, reader);
}, "~S,java.util.Map,~O");
Clazz.overrideMethod(c$, "processBinaryDocument", 
function(){
var t = System.currentTimeMillis();
this.binaryDoc.setBigEndian(true);
var msgMap = ( new JU.MessagePackReader(this.binaryDoc, false)).readMap();
this.binaryDoc.close();
this.version = msgMap.get("version");
System.out.println("BCIFReader: BCIF version " + this.version);
var dataBlock = (msgMap.get("dataBlocks"))[0];
System.out.println("BCIFReader processed MessagePack in " + (System.currentTimeMillis() - t) + " ms");
this.getCifDataParser();
var categories = dataBlock.get("categories");
this.bcifParser.header = dataBlock.get("header");
for (var j = 0; j < categories.length; j++) {
var cat = categories[j];
if (!cat.isEmpty()) this.processCategory(cat);
}
System.out.println("BCIFReader processed binary file in " + (System.currentTimeMillis() - t) + " ms");
});
Clazz.defineMethod(c$, "finalizeSubclassReader", 
function(){
Clazz.superCall(this, J.adapter.readers.cif.BCIFReader, "finalizeSubclassReader", []);
J.adapter.readers.cif.BCIFDecoder.clearTemp();
});
Clazz.defineMethod(c$, "processCategory", 
function(cat){
var catName = (cat.get("name")).toLowerCase();
if (!this.isCategoryOfInterest(catName)) return false;
this.bcifParser.initializeCategory(catName, J.adapter.readers.cif.BCIFDecoder.geMapInt(cat.get("rowCount")), cat.get("columns"));
this.processCategoryName(catName);
return false;
}, "java.util.Map");
Clazz.defineMethod(c$, "isCategoryOfInterest", 
function(catName){
switch (catName) {
case "_entry":
case "_atom_site":
case "_atom_type":
case "_atom_sites":
case "_cell":
case "_struct_ncs_oper":
case "_pdbx_struct_oper_list":
case "_pdbx_struct_assembly_gen":
case "_struct_ref_seq_dif":
case "_struct_site_gen":
case "_chem_comp":
case "_struct_conf":
case "_struct_sheet_range":
case "_chem_comp_bond":
case "_struct_conn":
return true;
}
return false;
}, "~S");
Clazz.defineMethod(c$, "processCategoryName", 
function(catName){
this.catName = catName;
switch (catName) {
case "_entry":
return this.processEntry();
case "_atom_site":
return this.processAtomSiteLoopBlock(false);
case "_atom_type":
return this.processAtomTypeLoopBlock();
case "_atom_sites":
return this.processAtomSites();
case "_cell":
return this.processCellBlock();
}
switch (catName) {
case "_struct_ncs_oper":
case "_pdbx_struct_oper_list":
case "_pdbx_struct_assembly_gen":
case "_struct_ref_seq_dif":
case "_struct_site_gen":
case "_chem_comp":
case "_struct_conf":
case "_struct_sheet_range":
case "_chem_comp_bond":
case "_struct_conn":
this.key0 = catName + ".";
return this.processSubclassLoopBlock();
}
return false;
}, "~S");
Clazz.defineMethod(c$, "processEntry", 
function(){
this.bcifParser.decodeAndGetData(0);
this.pdbID = this.bcifParser.fieldStr;
return true;
});
Clazz.defineMethod(c$, "processAtomSites", 
function(){
for (var i = 0; i < this.colCount; i++) {
this.bcifParser.decodeAndGetData(i);
this.processUnitCellTransformMatrix();
}
return true;
});
Clazz.defineMethod(c$, "processCellBlock", 
function(){
for (var i = 0; i < this.colCount; i++) {
this.bcifParser.decodeAndGetData(i);
this.processCellParameter();
}
return true;
});
Clazz.overrideMethod(c$, "parseLoopParameters", 
function(fields){
this.bcifParser.parseDataBlockParameters(fields, null, null, this.key2col, this.col2key);
}, "~A");
Clazz.overrideMethod(c$, "isFieldValid", 
function(){
if (this.bcifParser.fieldStr != null) this.firstChar = this.bcifParser.fieldStr.charAt(0);
return this.bcifParser.isFieldValid();
});
Clazz.overrideMethod(c$, "parseIntField", 
function(){
return this.bcifParser.ifield;
});
Clazz.overrideMethod(c$, "parseFloatField", 
function(){
return this.bcifParser.dfield;
});
Clazz.overrideMethod(c$, "parseCartesianField", 
function(){
return Math.round(this.bcifParser.dfield * 1000) / 1000;
});
Clazz.overrideMethod(c$, "parseIntFieldTok", 
function(tok){
this.getFieldString(tok);
return this.bcifParser.ifield;
}, "~N");
Clazz.overrideMethod(c$, "getFloatColumnData", 
function(i){
this.bcifParser.getColumnData(i);
return this.bcifParser.dfield;
}, "~N");
c$.temp = null;
});
;//5.0.1-v2 Fri Jun 07 15:32:46 BST 2024
