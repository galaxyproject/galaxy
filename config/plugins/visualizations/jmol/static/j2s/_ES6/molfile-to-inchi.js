import WASI from '../_WASM/wasi.esm.js';
/*
 * Creates [J2S|Jmol].molfileToInChI(molFileString) and .showInChIOptions()
 * 
 * Based on Richard Apodaca
 * https://github.com/rapodaca/inchi-wasm/blob/master/lib/molfile-to-inchi.js
 * 
 * An LLVM-generated Web Assembly implementation of InChI
 * 
 * 
 * Uses molfile_to_inchi.wasm and wasi.esm.js, from molfile_to_inchi.c
 * and InChI 1.05 
 * 
 * @author Rich Apodaca
 * @author Bob Hanson 2020.12.12
 * 
 * 
 */
const app = (self.J2S || self.Jmol || self);
const wasmPath = app.inchiPath || ".";
const memory = new WebAssembly.Memory({ initial: 10 });
const inputMaxBytes = app.inchiMaxBytes || 0x8000;
const outputMaxBytes = 0x4000;
(async () => {
  const response = await fetch(wasmPath + '/molfile_to_inchi.wasm');
  const bytes = await response.arrayBuffer();
  const wasi = new WASI();
  const { instance } = await WebAssembly.instantiate(bytes, {
    env: { memory }, wasi_snapshot_preview1: wasi.wasiImport
  });
  const pInput = instance.exports.malloc(inputMaxBytes);
  const pOptions = instance.exports.malloc(0x100);
  const pOutput = instance.exports.malloc(outputMaxBytes);

  app.showInChIOptions = () => {
   var s = "";

   //     s += ("-RTrip       Do a round trip test for each InChI generated\n");
  //      s += ("-Key         Generate InChIKey\n");
        s += ("-SNon        Exclude stereo (default: include absolute stereo)\n");
        s += ("-SRel        Relative stereo\n");
        s += ("-SRac        Racemic stereo\n");
  //      s += ("-SUCF        Use Chiral Flag: On means Absolute stereo, Off - Relative\n");
  //      s += ("-NEWPSOFF    Both ends of wedge point to stereocenters (default: a narrow end)\n");
        s += ("-DoNotAddH   All H are explicit (default: add H according to usual valences)\n");
        s += ("-SUU         Always include omitted unknown/undefined stereo\n");
        s += ("-SLUUD       Make labels for unknown and undefined stereo different\n");
        s += ("-FixedH      Include Fixed H layer\n");
        s += ("-RecMet      Include reconnected metals results\n");
        s += ("-KET         Account for keto-enol tautomerism (experimental)\n");
        s += ("-15T         Account for 1,5-tautomerism (experimental)\n");
  //      s += ("-AuxNone     Omit auxiliary information (default: Include)\n");
  //      s += ("-WarnOnEmptyStructure Warn and produce empty InChI for empty structure\n");
  //      s += ("-SaveOpt     Save custom InChI creation options (non-standard InChI)\n");
  //      s += ("-Wnumber     Set time-out per structure in seconds; W0 means unlimited\n");
  //      s += ("-LargeMolecules Treat molecules up to 32766 atoms (experimental)\n");
   alert(s);
 };

  app.molfileToInChI = (molfile,options) => {
    options || (options = "");
    if (molfile.length + 1 > inputMaxBytes) {
    	alert("Model data is over the maximum of " + inputMaxBytes + " bytes. \nYou can set this as Jmol.inchiMaxBytes.");
    	return "";
    } 
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    const inputView = new Uint8Array(memory.buffer);
    inputView.set(encoder.encode(molfile + "\0"), pInput);
    molfile = ""; // BH this is just so we can debug easier.
    inputView.set(encoder.encode(options + "\0"), pOptions);

    const result = instance.exports.molfile_to_inchi(pInput, pOptions, pOutput);

    const outputView = new Uint8Array(memory.buffer.slice(pOutput, pOutput + outputMaxBytes));
    const o = outputView.subarray(0, outputView.indexOf(0));
    const output = decoder.decode(o);

    if (result < 0 || result > 1) {
        alert("Error code " + result + " " + output.length);
    }
    
	return (options.toLowerCase().indexOf("key") >= 0 ? toKey(output) : output);
  };
  
  app.inchiToInchiKey = (inchi) => {
    return toKey(inchi);
  };
    
  const toKey = (inchi) => {
    const inputView = new Uint8Array(memory.buffer);
    
    inputView.set(new TextEncoder().encode(inchi + "\0"), pInput);
    
    const ret = instance.exports.inchi_to_inchikey(pInput, pOutput);
    const outputView = new Uint8Array(memory.buffer.slice(pOutput, pOutput + outputMaxBytes));
    
    return new TextDecoder().decode(outputView.subarray(0, outputView.indexOf(0)));
  };
  
  window.dispatchEvent(new Event('InChIReady'));

})();