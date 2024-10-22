""" Compute tool recommendations """

import json
import logging
import os

import h5py
import numpy as np
import yaml

from galaxy.tools.parameters import populate_state
from galaxy.tools.parameters.workflow_utils import workflow_building_modes
from galaxy.util import (
    DEFAULT_SOCKET_TIMEOUT,
    requests,
)
from galaxy.workflow.modules import module_factory

log = logging.getLogger(__name__)


class ToolRecommendations:
    max_seq_len = 25
    ff_dim = 128
    embed_dim = 128
    num_heads = 4
    dropout = 0.1

    def __init__(self):
        self.tool_recommendation_model_path = None
        self.admin_tool_recommendations_path = None
        self.deprecated_tools = {}
        self.admin_recommendations = {}
        self.model_data_dictionary = {}
        self.reverse_dictionary = {}
        self.all_tools = {}
        self.tool_weights_sorted = {}
        self.loaded_model = None
        self.compatible_tools = None
        self.standard_connections = None
        self.model_ok = None

    def create_transformer_model(self, vocab_size):
        try:
            from tensorflow.keras.layers import (
                Dense,
                Dropout,
                Embedding,
                GlobalAveragePooling1D,
                Input,
                Layer,
                LayerNormalization,
                MultiHeadAttention,
            )
            from tensorflow.keras.models import (
                Model,
                Sequential,
            )
        except Exception as e:
            log.exception(e)
            return None

        class TransformerBlock(Layer):
            def __init__(self, embed_dim, num_heads, ff_dim, rate=0.1):
                super().__init__()
                self.att = MultiHeadAttention(num_heads=num_heads, key_dim=embed_dim, dropout=rate)
                self.ffn = Sequential([Dense(ff_dim, activation="relu"), Dense(embed_dim)])
                self.layernorm1 = LayerNormalization(epsilon=1e-6)
                self.layernorm2 = LayerNormalization(epsilon=1e-6)
                self.dropout1 = Dropout(rate)
                self.dropout2 = Dropout(rate)

            def call(self, inputs, training):
                attn_output, attention_scores = self.att(
                    inputs, inputs, inputs, return_attention_scores=True, training=training
                )
                attn_output = self.dropout1(attn_output, training=training)
                out1 = self.layernorm1(inputs + attn_output)
                ffn_output = self.ffn(out1)
                ffn_output = self.dropout2(ffn_output, training=training)
                return self.layernorm2(out1 + ffn_output), attention_scores

        class TokenAndPositionEmbedding(Layer):
            def __init__(self, maxlen, vocab_size, embed_dim):
                super().__init__()
                self.token_emb = Embedding(input_dim=vocab_size, output_dim=embed_dim, mask_zero=True)
                self.pos_emb = Embedding(input_dim=maxlen, output_dim=embed_dim, mask_zero=True)

            def call(self, x):
                try:
                    import tensorflow as tf

                    maxlen = tf.shape(x)[-1]
                    positions = tf.range(start=0, limit=maxlen, delta=1)
                    positions = self.pos_emb(positions)
                    x = self.token_emb(x)
                    return x + positions
                except Exception as e:
                    log.exception(e)
                    return None

        inputs = Input(shape=(ToolRecommendations.max_seq_len,))
        embedding_layer = TokenAndPositionEmbedding(
            ToolRecommendations.max_seq_len, vocab_size, ToolRecommendations.embed_dim
        )
        x = embedding_layer(inputs)
        transformer_block = TransformerBlock(
            ToolRecommendations.embed_dim, ToolRecommendations.num_heads, ToolRecommendations.ff_dim
        )
        x, weights = transformer_block(x)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(ToolRecommendations.dropout)(x)
        x = Dense(ToolRecommendations.ff_dim, activation="relu")(x)
        x = Dropout(ToolRecommendations.dropout)(x)
        outputs = Dense(vocab_size, activation="sigmoid")(x)
        return Model(inputs=inputs, outputs=[outputs, weights])

    def get_predictions(self, trans, tool_sequence, remote_model_url):
        """
        Compute tool predictions
        """
        recommended_tools = {}
        self.__collect_admin_preferences(trans.app.config.admin_tool_recommendations_path)
        if self.model_ok is None:
            self.__set_model(trans, remote_model_url)
        recommended_tools = self.__compute_tool_prediction(trans, tool_sequence)
        return tool_sequence, recommended_tools

    def __set_model(self, trans, remote_model_url):
        """
        Create model and associated dictionaries for recommendations
        """
        self.tool_recommendation_model_path = self.__download_model(remote_model_url)
        with h5py.File(self.tool_recommendation_model_path, "r", locking=False) as model_file:
            self.reverse_dictionary = json.loads(model_file["reverse_dict"][()].decode("utf-8"))
            self.loaded_model = self.create_transformer_model(len(self.reverse_dictionary) + 1)
            self.loaded_model.load_weights(self.tool_recommendation_model_path)

            self.model_data_dictionary = {v: k for k, v in self.reverse_dictionary.items()}
            # set the list of compatible tools
            self.compatible_tools = json.loads(model_file["compatible_tools"][()].decode("utf-8"))
            tool_weights = json.loads(model_file["class_weights"][()].decode("utf-8"))
            self.standard_connections = json.loads(model_file["standard_connections"][()].decode("utf-8"))
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
        self.model_ok = True

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
        input_extensions = []
        output_extensions = []
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
        prediction_data["is_deprecated"] = False
        # get the list of datatype extensions of the last tool of the tool sequence
        _, last_output_extensions = self.__get_tool_extensions(trans, self.all_tools[last_tool_name][0])
        prediction_data["o_extensions"] = list(set(last_output_extensions))
        t_ids_scores = zip(tool_ids, tool_scores)
        # form the payload of the predicted tools to be shown
        for child, score in t_ids_scores:
            c_dict = {}
            for t_id in self.all_tools:
                # select the name and tool id if it is installed in Galaxy
                if t_id == child and score >= 0.0 and child not in self.deprecated_tools and child != last_tool_name:
                    full_tool_id = self.all_tools[t_id][0]
                    pred_input_extensions, _ = self.__get_tool_extensions(trans, full_tool_id)
                    c_dict["name"] = self.all_tools[t_id][1]
                    c_dict["tool_id"] = full_tool_id
                    c_dict["tool_score"] = score
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

    def __get_predicted_tools(self, pub_tools, predictions, last_tool_name, topk):
        """
        Get predicted tools. If predicted tools are less in number, combine them with published tools
        """
        last_compatible_tools = []
        if last_tool_name in self.model_data_dictionary:
            last_tool_name_id = self.model_data_dictionary[last_tool_name]
            if last_tool_name_id in self.compatible_tools:
                last_compatible_tools = [
                    self.reverse_dictionary[t_id] for t_id in self.compatible_tools[last_tool_name_id]
                ]
        t_intersect = list(set(predictions).intersection(set(pub_tools)))
        t_diff = list(set(predictions).difference(set(pub_tools)))
        t_intersect, u_intersect = self.__sort_by_usage(
            t_intersect, self.tool_weights_sorted, self.model_data_dictionary
        )
        t_diff, u_diff = self.__sort_by_usage(t_diff, self.tool_weights_sorted, self.model_data_dictionary)
        t_intersect_compat = list(set(last_compatible_tools).intersection(set(t_diff)))
        # filter against rare bad predictions for any tool
        if len(t_intersect_compat) > 0:
            t_compat, u_compat = self.__sort_by_usage(
                t_intersect_compat, self.tool_weights_sorted, self.model_data_dictionary
            )
        else:
            t_compat, u_compat = self.__sort_by_usage(
                last_compatible_tools, self.tool_weights_sorted, self.model_data_dictionary
            )
        t_intersect.extend(t_compat)
        u_intersect.extend(u_compat)
        t_intersect = t_intersect[:topk]
        u_intersect = u_intersect[:topk]
        return t_intersect, u_intersect

    def __sort_by_usage(self, t_list, class_weights, d_dict):
        """
        Sort predictions by usage/class weights
        """
        tool_dict = {}
        for tool in t_list:
            t_id = d_dict[tool]
            tool_dict[tool] = class_weights[int(t_id)]
        tool_dict = dict(sorted(tool_dict.items(), key=lambda kv: kv[1], reverse=True))
        return list(tool_dict.keys()), list(tool_dict.values())

    def __separate_predictions(self, base_tools, predictions, last_tool_name, weight_values, topk):
        """
        Get predictions from published and normal workflows
        """
        last_base_tools = []
        weight_values = list(self.tool_weights_sorted.values())
        wt_predictions = predictions * weight_values
        prediction_pos = np.argsort(predictions, axis=-1)
        wt_prediction_pos = np.argsort(wt_predictions, axis=-1)
        topk_prediction_pos = list(prediction_pos[-topk:])
        wt_topk_prediction_pos = list(wt_prediction_pos[-topk:])
        # get tool ids
        wt_pred_tool_names = [self.reverse_dictionary[str(tool_pos)] for tool_pos in wt_topk_prediction_pos]
        pred_tool_names = [self.reverse_dictionary[str(tool_pos)] for tool_pos in topk_prediction_pos]
        # exclude same tool as the last tool
        pred_tool_names.extend(wt_pred_tool_names)
        pred_tool_names = [item for item in pred_tool_names if item != last_tool_name]
        if last_tool_name in base_tools:
            last_base_tools = base_tools[last_tool_name]
            if type(last_base_tools).__name__ == "str":
                # get published or compatible tools for the last tool in a sequence of tools
                last_base_tools = last_base_tools.split(",")
        # get predicted tools
        sorted_c_t, sorted_c_v = self.__get_predicted_tools(last_base_tools, pred_tool_names, last_tool_name, topk)
        return sorted_c_t, sorted_c_v

    def __compute_tool_prediction(self, trans, tool_sequence):
        """
        Compute the predicted tools for a tool sequences
        Return a payload with the tool sequences and recommended tools
        Return an empty payload with just the tool sequence if anything goes wrong within the try block
        """
        topk = trans.app.config.topk_recommendations
        prediction_data = {}
        tool_sequence = tool_sequence.split(",")[::-1]
        prediction_data["name"] = ",".join(tool_sequence)
        prediction_data["children"] = []
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
                import tensorflow as tf

                sample = tf.convert_to_tensor(sample, dtype=tf.int64)
                prediction, _ = self.loaded_model(sample, training=False)
            except Exception as e:
                log.exception(e)
                return prediction_data
            # get dimensions
            nw_dimension = prediction.shape[1]
            prediction = np.reshape(prediction, (nw_dimension,))
            # get recommended tools from published workflows
            pub_t, pub_v = self.__separate_predictions(
                self.standard_connections, prediction, last_tool_name, weight_values, topk
            )
            prediction_data = self.__filter_tool_predictions(trans, prediction_data, pub_t, pub_v, last_tool_name)
        return prediction_data
