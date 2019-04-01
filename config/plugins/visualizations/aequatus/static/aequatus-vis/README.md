# aequatus.js
Visualisation JavaScript library for Homologous Genes 

# Usage

Aequatus.js is a visualisation JavaScript library for Homologous Genes, easy to integrate with existing web services.

To use aequatus.js in your webservice use following simple snippet.

```javascript
var syntenic_data = json;
init(syntenic_data, "#settings_div", "#filter", "#sliderfilter");
drawTree(syntenic_data.tree, "#gene_tree", popup);
```

where `settings_div`, `filter_div` and `sliderfilter` are ids for the divs to hold various controls, filter options and slider; and `popup` is a callback for JavaScript function when clicked on any gene.

An example popup is included in the demo.

Functions:
```javascript
changeReference(new_gene_id, new_protein_id)
```
It is used to change reference gene in showing gene families.

# Data Format
An Example dataset is provided in the demo/data directory. 

snapshot:
```
{
  "ref":<ref gene id>,
  "protein_id":<ref protein id>,
  "tree":<genetree in JSON>
  "member":<JSON formatted genes array>
}
```

In which genetree and each gene information can be downloaded from Ensembl using REST API. 

1. Ensembl REST for genetree: http://rest.ensembl.org/documentation/info/genetree
2. Ensembl REST for gene: http://rest.ensembl.org/documentation/info/lookup

# License

aequatus.js is free software: you can redistribute it and/or modify it under the terms of the GMITL License.

aequatus.js is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.


# <a name="contacts"></a> Project contacts: 
* Anil Thanki <Anil.Thanki@earlham.ac.uk>
* Robert Davey <Robert.Davey@earlham.ac.uk>


© 2015 - 2018. Earlham Institute, Norwich, UK

