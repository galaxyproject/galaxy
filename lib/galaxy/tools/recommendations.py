""" Compute tool recommendations """

import json
import logging
import os

import h5py
import numpy as np
import requests
import yaml

from galaxy.tools.parameters import populate_state
from galaxy.tools.parameters.basic import workflow_building_modes
from galaxy.util import DEFAULT_SOCKET_TIMEOUT
from galaxy.workflow.modules import module_factory

log = logging.getLogger(__name__)


class ToolRecommendations:
    def __init__(self):
        self.tool_recommendation_model_path = None
        self.admin_tool_recommendations_path = None
        self.deprecated_tools = dict()
        self.admin_recommendations = dict()
        self.model_data_dictionary = dict()
        self.reverse_dictionary = dict()
        self.all_tools = dict()
        self.tool_weights_sorted = dict()
        self.session = None
        self.graph = None
        self.loaded_model = None
        self.compatible_tools = None
        self.standard_connections = None
        self.max_seq_len = 25

    def get_predictions(self, trans, tool_sequence, remote_model_url):
        """
        Compute tool predictions
        """
        recommended_tools = dict()
        self.__collect_admin_preferences(trans.app.config.admin_tool_recommendations_path)
        is_set = self.__set_model(trans, remote_model_url)
        if is_set is True:
            # get the recommended tools for a tool sequence
            recommended_tools = self.__compute_tool_prediction(trans, tool_sequence)
        else:
            tool_sequence = ""
        return tool_sequence, recommended_tools

    def __set_model(self, trans, remote_model_url):
        """
        Create model and associated dictionaries for recommendations
        """
        if not self.graph:
            # import moves from the top of file: in case the tool recommendation feature is disabled,
            # keras is not downloaded because of conditional requirement and Galaxy does not build
            try:
                import tensorflow as tf

                tf.compat.v1.disable_v2_behavior()
            except Exception:
                trans.response.status = 400
                return False
            # set graph and session only once
            if self.graph is None:
                self.graph = tf.Graph()
                self.session = tf.compat.v1.Session(graph=self.graph)
            model_weights = list()
            counter_layer_weights = 0
            self.tool_recommendation_model_path = self.__download_model(remote_model_url)
            # read the hdf5 attributes
            trained_model = h5py.File(self.tool_recommendation_model_path, "r")
            model_config = json.loads(trained_model["model_config"][()])
            # set tensorflow's graph and session to maintain
            # consistency between model load and predict methods
            with self.graph.as_default():
                with self.session.as_default():
                    try:
                        # iterate through all the attributes of the model to find weights of neural network layers
                        for item in trained_model.keys():
                            if "weight_" in item:
                                weight = trained_model[f"weight_{str(counter_layer_weights)}"][()]
                                model_weights.append(weight)
                                counter_layer_weights += 1
                        self.loaded_model = tf.keras.models.model_from_json(model_config)
                        self.loaded_model.set_weights(model_weights)
                    except Exception as e:
                        log.exception(e)
                        trans.response.status = 400
                        return False
            # set the dictionary of tools
            self.model_data_dictionary = json.loads(trained_model["data_dictionary"][()])
            self.reverse_dictionary = {v: k for k, v in self.model_data_dictionary.items()}
            # set the list of compatible tools
            self.compatible_tools = json.loads(trained_model["compatible_tools"][()])
            tool_weights = json.loads(trained_model["class_weights"][()])
            self.standard_connections = json.loads(trained_model["standard_connections"][()])
            # sort the tools' usage dictionary
            tool_pos_sorted = [int(key) for key in tool_weights.keys()]
            for k in tool_pos_sorted:
                self.tool_weights_sorted[k] = tool_weights[str(k)]
            # collect ids and names of all the installed tools
            for tool_id, tool in trans.app.toolbox.tools():
                t_id_renamed = tool_id
                if t_id_renamed.find("/") > -1:
                    t_id_renamed = t_id_renamed.split("/")[-2]
                self.all_tools[t_id_renamed] = (tool_id, tool.name)
        return True

    def __collect_admin_preferences(self, admin_path):
        """
        Collect preferences for recommendations of tools
        set by admins as dictionaries of deprecated tools and
        additional recommendations
        """
        if not self.admin_tool_recommendations_path and admin_path is not None:
            self.admin_tool_recommendations_path = os.path.join(os.getcwd(), admin_path)
            if os.path.exists(self.admin_tool_recommendations_path):
                with open(self.admin_tool_recommendations_path) as admin_recommendations:
                    admin_recommendation_preferences = yaml.safe_load(admin_recommendations)
                    if admin_recommendation_preferences:
                        for tool_id in admin_recommendation_preferences:
                            tool_info = admin_recommendation_preferences[tool_id]
                            if "is_deprecated" in tool_info[0]:
                                self.deprecated_tools[tool_id] = tool_info[0]["text_message"]
                            else:
                                if tool_id not in self.admin_recommendations:
                                    self.admin_recommendations[tool_id] = tool_info

    def __download_model(self, model_url, download_local="database/"):
        """
        Download the model from remote server
        """
        local_dir = os.path.join(os.getcwd(), download_local, "tool_recommendation_model.hdf5")
        # read model from remote
        model_binary = requests.get(model_url, timeout=DEFAULT_SOCKET_TIMEOUT)
        # save model to a local directory
        with open(local_dir, "wb") as model_file:
            model_file.write(model_binary.content)
            return local_dir

    def __get_tool_extensions(self, trans, tool_id):
        """
        Get the input and output extensions of a tool
        """
        payload = {"type": "tool", "tool_id": tool_id, "_": "true"}
        inputs = payload.get("inputs", {})
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        module = module_factory.from_dict(trans, payload)
        if "tool_state" not in payload:
            module_state = {}
            populate_state(trans, module.get_inputs(), inputs, module_state, check=False)
            module.recover_state(module_state)
        inputs = module.get_all_inputs(connectable_only=True)
        outputs = module.get_all_outputs()
        input_extensions = list()
        output_extensions = list()
        for i_ext in inputs:
            input_extensions.extend(i_ext["extensions"])
        for o_ext in outputs:
            output_extensions.extend(o_ext["extensions"])
        return input_extensions, output_extensions

    def __filter_tool_predictions(self, trans, prediction_data, tool_ids, tool_scores, last_tool_name):
        """
        Filter tool predictions based on datatype compatibility and tool connections.
        Add admin preferences to recommendations.
        """
        last_compatible_tools = list()
        if last_tool_name in self.compatible_tools:
            last_compatible_tools = self.compatible_tools[last_tool_name].split(",")
        prediction_data["is_deprecated"] = False
        # get the list of datatype extensions of the last tool of the tool sequence
        _, last_output_extensions = self.__get_tool_extensions(trans, self.all_tools[last_tool_name][0])
        prediction_data["o_extensions"] = list(set(last_output_extensions))
        t_ids_scores = zip(tool_ids, tool_scores)
        # form the payload of the predicted tools to be shown
        for child, score in t_ids_scores:
            c_dict = dict()
            for t_id in self.all_tools:
                # select the name and tool id if it is installed in Galaxy
                if (
                    t_id == child
                    and score > 0.0
                    and child in last_compatible_tools
                    and child not in self.deprecated_tools
                ):
                    full_tool_id = self.all_tools[t_id][0]
                    pred_input_extensions, _ = self.__get_tool_extensions(trans, full_tool_id)
                    c_dict["name"] = self.all_tools[t_id][1]
                    c_dict["tool_id"] = full_tool_id
                    c_dict["i_extensions"] = list(set(pred_input_extensions))
                    prediction_data["children"].append(c_dict)
                    break
        # incorporate preferences set by admins
        if self.admin_tool_recommendations_path:
            # filter out deprecated tools
            t_ids_scores = [
                (tid, score) for tid, score in zip(tool_ids, tool_scores) if tid not in self.deprecated_tools
            ]
            # set the property if the last tool of the sequence is deprecated
            if last_tool_name in self.deprecated_tools:
                prediction_data["is_deprecated"] = True
                prediction_data["message"] = self.deprecated_tools[last_tool_name]
            # add the recommendations given by admins
            for tool_id in self.admin_recommendations:
                if last_tool_name == tool_id:
                    admin_recommendations = self.admin_recommendations[tool_id]
                    if trans.app.config.overwrite_model_recommendations is True:
                        prediction_data["children"] = admin_recommendations
                    else:
                        prediction_data["children"].extend(admin_recommendations)
                    break
        # get the root name for displaying after tool run
        for t_id in self.all_tools:
            if t_id == last_tool_name:
                prediction_data["name"] = self.all_tools[t_id][1]
                break
        return prediction_data

    def __get_predicted_tools(self, base_tools, predictions, topk):
        """
        Get predicted tools. If predicted tools are less in number, combine them with published tools
        """
        intersection = list(set(predictions).intersection(set(base_tools)))
        return intersection[:topk]

    def __sort_by_usage(self, t_list, class_weights, d_dict):
        """
        Sort predictions by usage/class weights
        """
        tool_dict = dict()
        for tool in t_list:
            t_id = d_dict[tool]
            tool_dict[tool] = class_weights[t_id]
        tool_dict = dict(sorted(tool_dict.items(), key=lambda kv: kv[1], reverse=True))
        return list(tool_dict.keys()), list(tool_dict.values())

    def __separate_predictions(self, base_tools, predictions, last_tool_name, weight_values, topk):
        """
        Get predictions from published and normal workflows
        """
        last_base_tools = list()
        predictions = predictions * weight_values
        prediction_pos = np.argsort(predictions, axis=-1)
        topk_prediction_pos = prediction_pos[-topk:]
        # get tool ids
        pred_tool_ids = [self.reverse_dictionary[int(tool_pos)] for tool_pos in topk_prediction_pos]
        if last_tool_name in base_tools:
            last_base_tools = base_tools[last_tool_name]
            if type(last_base_tools).__name__ == "str":
                # get published or compatible tools for the last tool in a sequence of tools
                last_base_tools = last_base_tools.split(",")
        # get predicted tools
        p_tools = self.__get_predicted_tools(last_base_tools, pred_tool_ids, topk)
        sorted_c_t, sorted_c_v = self.__sort_by_usage(p_tools, self.tool_weights_sorted, self.model_data_dictionary)
        return sorted_c_t, sorted_c_v

    def __compute_tool_prediction(self, trans, tool_sequence):
        """
        Compute the predicted tools for a tool sequences
        Return a payload with the tool sequences and recommended tools
        Return an empty payload with just the tool sequence if anything goes wrong within the try block
        """
        topk = trans.app.config.topk_recommendations
        prediction_data = dict()
        tool_sequence = tool_sequence.split(",")[::-1]
        prediction_data["name"] = ",".join(tool_sequence)
        prediction_data["children"] = list()
        last_tool_name = tool_sequence[-1]
        # do prediction only if the last is present in the collections of tools
        if last_tool_name in self.model_data_dictionary:
            sample = np.zeros(self.max_seq_len)
            # get tool names without slashes and create a sequence vector
            for idx, tool_name in enumerate(tool_sequence):
                if tool_name.find("/") > -1:
                    tool_name = tool_name.split("/")[-2]
                try:
                    sample[idx] = int(self.model_data_dictionary[tool_name])
                except Exception:
                    log.exception(f"Failed to find tool {tool_name} in model")
                    return prediction_data
            sample = np.reshape(sample, (1, self.max_seq_len))
            # boost the predicted scores using tools' usage
            weight_values = list(self.tool_weights_sorted.values())
            # predict next tools for a test path
            try:
                # use the same graph and session to predict
                with self.graph.as_default():
                    with self.session.as_default():
                        prediction = self.loaded_model.predict(sample)
            except Exception as e:
                log.exception(e)
                return prediction_data
            # get dimensions
            nw_dimension = prediction.shape[1]
            prediction = np.reshape(prediction, (nw_dimension,))
            half_len = int(nw_dimension / 2)
            # get recommended tools from published workflows
            pub_t, pub_v = self.__separate_predictions(
                self.standard_connections, prediction[:half_len], last_tool_name, weight_values, topk
            )
            # get recommended tools from normal workflows
            c_t, c_v = self.__separate_predictions(
                self.compatible_tools, prediction[half_len:], last_tool_name, weight_values, topk
            )
            # combine predictions coming from different workflows
            # promote recommended tools coming from published workflows
            # to the top and then show other recommendations
            pub_t.extend(c_t)
            pub_v.extend(c_v)
            # remove duplicates if any
            pub_t = list(dict.fromkeys(pub_t))
            pub_v = list(dict.fromkeys(pub_v))
            prediction_data = self.__filter_tool_predictions(trans, prediction_data, pub_t, pub_v, last_tool_name)
        return prediction_data
