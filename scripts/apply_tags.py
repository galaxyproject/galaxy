""" Apply tags to the inherited history items of Galaxy """

import sys
import time

from bioblend.galaxy import GalaxyInstance


class ApplyTagsHistory(object):

    @classmethod
    def __init__(self, galaxy_url, galaxy_api_key, history_id=None):
        self.galaxy_url = galaxy_url
        self.galaxy_api_key = galaxy_api_key
        self.history_id = history_id

    @classmethod
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
                print("Some problem occurred with history: %s" % self.history_id)
                print(exception)
                return
        update_history_id = update_history["id"]
        print("History name: %s" % update_history["name"])
        print("History id: %s" % update_history_id)
        self.find_dataset_parents_update_tags(history, job, update_history_id)

    @classmethod
    def find_dataset_parents_update_tags(self, history, job, history_id):
        """
        Operate on datasets for a particular history and recursively find parents
        for a dataset
        """
        datasets_inheritance_chain = dict()
        own_tags = dict()
        parent_tags = dict()
        count_datasets_updated = 0
        # get all datasets belonging to a history
        all_datasets = history.show_history(history_id, contents=True)
        print("Total datasets: %d. Updating their tags may take a while..." % len(all_datasets))
        for dataset in all_datasets:
            try:
                if dataset["deleted"] is False and dataset["state"] == 'ok':
                    parent_ids = list()
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
                is_updated = self.propagate_tags(history, history_id, parent_dataset_ids, dataset_id, parent_tags, own_tags)
                if is_updated is True:
                    count_datasets_updated += 1
        print("Tags of %d datasets updated" % count_datasets_updated)

    @classmethod
    def collect_parent_ids(self, datasets_inheritance_chain):
        """
        Collect parent datasets for each dataset recursively
        """
        recursive_parent_ids = dict()
        for item in datasets_inheritance_chain:
            recursive_parents = list()

            def find_parent_recursive(dataset_id):
                if dataset_id in datasets_inheritance_chain:
                    # get parents of a dataset
                    dataset_parents = datasets_inheritance_chain[dataset_id]
                    # add all the parents to the recursive list
                    recursive_parents.extend(dataset_parents)
                    for parent in dataset_parents:
                        find_parent_recursive(parent)
            find_parent_recursive(item)
            # take unique parents
            recursive_parent_ids[item] = list(set(recursive_parents))
        return recursive_parent_ids

    @classmethod
    def collect_hash_tags(self, tags_list):
        """
        Collect only hash tags and exclude others if any
        """
        return [tag for tag in tags_list if len(tag.split(":")) > 1]

    @classmethod
    def propagate_tags(self, history, current_history_id, parent_datasets_ids, dataset_id, parent_tags, own_tags):
        """
        Propagate history tags from parent(s) to a child
        """
        all_tags = list()
        for parent_id in parent_datasets_ids:
            # collect all the tags from the parent
            all_tags.extend(parent_tags[parent_id])
        # take only hash tags
        all_tags = self.collect_hash_tags(all_tags)
        self_tags = self.collect_hash_tags(own_tags[dataset_id])
        # find unique tags from all parents
        all_tags = set(all_tags)
        self_tags_set = set(self_tags)
        is_same = (all_tags == self_tags_set)
        # update tags if there are new tags from parents
        if is_same is False:
            is_subset = all_tags.issubset(self_tags_set)
            if is_subset is False:
                # append the tags of the child itself
                all_tags = list(all_tags)
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
    print("Program finished in %d seconds" % int(end_time - start_time))
