# Galaxy Graph Visualization Framework  #

The framework visualizes graphs and tries to provide functionality to easily manipulate them in Galaxy platform. 
For graph construction and visualization [Cytoscape.js](http://js.cytoscape.org/) library is used.

### Input formats ###

As input files json or txt formats can be used. 

Examples: 

* json file 
   
```
#!json

{
  "nodes":[
			{
				"id": 1,
			},
			{
				"id": 2,
			}
          ],
 "links":[
			
			{
				"source":1,
				"target":2,
			}
         ]
}

```

* txt file with matrix notation


```
#!python

1	3 4 5
2	4 6
3	1 5 6 2
4	3
5	
6
```
Line "1	 3 4 5" can be read as: source: node "1" , target: node "3" ("4","5")


### General Description ###

The framework consists of 3 parts. On the left and right sides of the screen are 2 sliding panels. By default they are hidden. They can be opened by clicking the button on the upper part of each panel. The left panel is  Tool Panel where user can choose different features to manipulate the graph. On the right panel all available node information (metadata) is displayed. 
In between these panels is the main screen where the visualization is displayed.


### Features ###

| Feature      | Description                    |
| ------------- | ------------------------------ |
| Lazy loading      |    If the graph contains more than 50 nodes lazy loading will be performed. At first the framework will load only the root nodes(nodes that have no incoming edges) and their child nodes. The child nodes that can be expanded (contain other nodes) will have bigger size. To load the rest of the graph *Expand* feature must be used on the expandable nodes. It's working only if the graph has at least one root node |
| Delete   | Deletes selected nodes and edges. Can be performed by using corresponding button or shortcut key 'd'     |
| Restore   | Restores the deleted nodes and edges form the very last deletion performed     |
| Collapse   | Collapse feature can be performed on the selected node which has   outgoing edges. It hides all outgoing (child) nodes and edges of the selected node. Useful for compact view. Can be performed by using corresponding button or shortcut key 'c'. To uncollapse the node *Expand* or *Restore Structure* can be used      |
|Expand| Expand feature can be used to load more nodes in case if lazy loading was used or to uncollapse collapsed nodes.Can be performed by using corresponding button or shortcut key 'e'     |
|Metadata | Node metadata is always displayed on the right panel  |
|Child/parent dependencies| To see incoming/outgoing nodes and edges of the selected node enable (check) corresponding feature on the left panel |
|Labels| Node and edge labels can be shown/hidden by enabling/disabling corresponding option on the left Panel |
|Export PNG| It is possible to export the visualization of the graph as a png picture. To perform the action click on the corresponding button |