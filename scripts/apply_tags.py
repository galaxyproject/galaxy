""" Apply tags to the inherited history items of Galaxy """

import sys
import time
from typing import List

from bioblend.galaxy import GalaxyInstance


class ApplyTagsHistory:
    def __init__(self, galaxy_url, galaxy_api_key, history_id=None):
        self.galaxy_url = galaxy_url
        self.galaxy_api_key = galaxy_api_key
        self.history_id = history_id

    def read_galaxy_history(self):
        """
        Read Galaxy's current history and inherit all the tags from a parent
        to a child history item
        """
        # connect to running Galaxy's instance
        g_instance = GalaxyInstance(self.galaxy_url, self.galaxy_api_key, self.history_id)
        history = g_instance.histories
        job = g_instance.jobs
        # if the history id is not supplied, then update tags for the most recently used history
        if self.history_id is None:
            update_history = history.get_most_recently_used_history()
        else:
            try:
                update_history = history.show_history(self.history_id)
            except Exception as exception:
                print(f"Some problem occurred with history: {self.history_id}")
                print(exception)
                return
        update_history_id = update_history["id"]
        print(f"History name: {update_history['name']}")
        print(f"History id: {update_history_id}")
        self.find_dataset_parents_update_tags(history, job, update_history_id)

    def find_dataset_parents_update_tags(self, history, job, history_id):
        """
        Operate on datasets for a particular history and recursively find parents
        for a dataset
        """
        datasets_inheritance_chain = {}
        own_tags = {}
        parent_tags = {}
        count_datasets_updated = 0
        # get all datasets belonging to a history
        all_datasets = history.show_history(history_id, contents=True)
        print(f"Total datasets: {len(all_datasets)}. Updating their tags may take a while...")
        for dataset in all_datasets:
            try:
                if not dataset["deleted"] and dataset["state"] == "ok":
                    parent_ids = []
                    child_dataset_id = dataset["id"]
                    own_tags[child_dataset_id] = dataset["tags"]
                    # get information about the dataset like the job id
                    # used in its creation. One parameter "inputs" from the job details lists all the dataset id(s)
                    # used in creating the current dataset which is/are its parent datasets.
                    dataset_info = history.show_dataset_provenance(history_id, child_dataset_id, False)
                    job_details = job.show_job(dataset_info["job_id"], True)
                    if "inputs" in job_details:
                        # get all the inputs for the job that created this dataset.
                        # these inputs are the parent datasets of the current dataset
                        job_inputs = job_details["inputs"]
                        for item in job_inputs:
                            parent_id = job_inputs[item]["id"]
                            try:
                                if parent_id not in parent_tags:
                                    parent_dataset = history.show_dataset(history_id, parent_id)
                                    if not parent_dataset["deleted"]:
                                        parent_tags[parent_id] = parent_dataset["tags"]
                                        parent_ids.append(parent_id)
                                else:
                                    parent_ids.append(parent_id)
                            except Exception:
                                pass
                    datasets_inheritance_chain[child_dataset_id] = parent_ids
            except Exception:
                pass
        # collect all the parents for each dataset recursively
        all_parents = self.collect_parent_ids(datasets_inheritance_chain)
        # update tags
        for dataset_id in all_parents:
            parent_dataset_ids = all_parents[dataset_id]
            # update history tags for a dataset taking all from its parents if there is a parent
            if len(parent_dataset_ids) > 0:
                is_updated = self.propagate_tags(
                    history, history_id, parent_dataset_ids, dataset_id, parent_tags, own_tags
                )
                if is_updated:
                    count_datasets_updated += 1
        print(f"Tags of {count_datasets_updated} datasets updated")

    def collect_parent_ids(self, datasets_inheritance_chain):
        """
        Collect parent datasets for each dataset recursively
        """

        def find_parent_recursive(dataset_id, recursive_parents):
            if dataset_id in datasets_inheritance_chain:
                # get parents of a dataset
                dataset_parents = datasets_inheritance_chain[dataset_id]
                # add all the parents to the recursive list
                recursive_parents.extend(dataset_parents)
                for parent in dataset_parents:
                    find_parent_recursive(parent, recursive_parents)

        recursive_parent_ids = {}
        for item in datasets_inheritance_chain:
            recursive_parents: List = []

            find_parent_recursive(item, recursive_parents)
            # take unique parents
            recursive_parent_ids[item] = list(set(recursive_parents))
        return recursive_parent_ids

    @staticmethod
    def collect_hash_tags(tags_list):
        """
        Collect only hash tags and exclude others if any
        """
        return [tag for tag in tags_list if len(tag.split(":")) > 1]

    def propagate_tags(self, history, current_history_id, parent_datasets_ids, dataset_id, parent_tags, own_tags):
        """
        Propagate history tags from parent(s) to a child
        """
        all_tags = []
        for parent_id in parent_datasets_ids:
            # collect all the tags from the parent
            all_tags.extend(parent_tags[parent_id])
        # take only hash tags
        all_tags = self.collect_hash_tags(all_tags)
        self_tags = self.collect_hash_tags(own_tags[dataset_id])
        # find unique tags from all parents
        all_tags_set = set(all_tags)
        # update tags if there are new tags from parents
        if all_tags_set != (self_tags_set := set(self_tags)):
            if not all_tags_set.issubset(self_tags_set):
                # append the tags of the child itself
                all_tags.extend(self_tags)
                # do a database update for the child dataset so that it reflects the tags from all parents
                # take unique tags
                history.update_dataset(current_history_id, dataset_id, tags=all_tags)
                return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python apply_tags.py <galaxy_ip> <galaxy_api_key> <history_id as optional parameter>")
        exit(1)
    start_time = time.time()
    history_id = None
    if len(sys.argv) > 3:
        history_id = sys.argv[3]
    history_tags = ApplyTagsHistory(sys.argv[1], sys.argv[2], history_id)
    history_tags.read_galaxy_history()
    end_time = time.time()
    print(f"Program finished in {int(end_time - start_time)} seconds")
