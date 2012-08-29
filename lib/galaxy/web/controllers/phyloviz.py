import pkg_resources
pkg_resources.require( "bx-python" )

from galaxy.util.json import to_json_string, from_json_string
from galaxy.web.base.controller import *
from galaxy.visualization.phyloviz.phyloviz_dataprovider import Phyloviz_DataProvider


class PhyloVizController( BaseUIController, UsesVisualizationMixin, UsesHistoryDatasetAssociationMixin, SharableMixin ):
    """
    Controller for phyloViz browser interface.
    """
    def __init__(self, app ):
        BaseUIController.__init__( self, app )

    @web.expose
    @web.require_login()
    def index( self, trans, dataset_id = None, **kwargs ):
        """
        The index method is called using phyloviz/ with a dataset id passed in.
        The relevant data set is then retrieved via get_json_from_datasetId which interfaces with the parser
        The json representation of the phylogenetic tree along with the config is then written in the .mako template and passed back to the user
        """
        json, config = self.get_json_from_datasetId(trans, dataset_id)
        config["saved_visualization"] = False
        return trans.fill_template( "visualization/phyloviz.mako", data = json, config=config)


    @web.expose
    def visualization(self, trans, id):
        """
        Called using a viz_id (id) to retrieved stored visualization data (in json format) and all the viz_config
        """
        viz = self.get_visualization(trans, id)
        config = self.get_visualization_config(trans, viz)
        config["saved_visualization"] = True
        data = config["root"]

        return trans.fill_template( "visualization/phyloviz.mako", data = data, config=config)


    @web.expose
    @web.json
    def load_visualization_json(self, trans, viz_id):
        """
        Though not used in current implementation, this provides user with a convenient method to retrieve the viz_data & viz_config via json.
        """
        viz = self.get_visualization(trans, viz_id)
        viz_config = self.get_visualization_config(trans, viz)
        viz_config["saved_visualization"] = True
        return {
            "data" : viz_config["root"],
            "config" : viz_config
        }


    @web.expose
    @web.json
    def getJsonData(self, trans, dataset_id, treeIndex=0):
        """
        Method to retrieve data asynchronously via json format. Retriving from here rather than
        making a direct datasets/ call allows for some processing and event capturing
        """
        treeIndex = int(treeIndex)
        json, config = self.get_json_from_datasetId(trans, dataset_id, treeIndex)
        packedJson = {
            "data" : json,
            "config" : config
        }

        return packedJson


    def get_json_from_datasetId(self, trans, dataset_id, treeIndex=0):
        """
        For interfacing phyloviz controllers with phyloviz visualization data provider (parsers)
        """
        dataset = self.get_dataset(trans, dataset_id)
        fileExt, filepath  = dataset.ext, dataset.file_name      # .name stores the name of the dataset from the orginal upload
        json, config = "", {}         #        config contains properties of the tree and file

        if fileExt == "json":
            something, json = self.get_data(dataset)
        else:
            try:
                pd = Phyloviz_DataProvider()
                json, config = pd.parseFile(filepath, fileExt)
                json = json[treeIndex]
            except Exception:
                pass

        config["title"] = dataset.display_name()
        config["ext"] = fileExt
        config["dataset_id"] = dataset_id
        config["treeIndex"] = treeIndex

        return json, config
