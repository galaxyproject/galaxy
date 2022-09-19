from galaxy.job_execution.datasets import DatasetPath


def test_dataset_path():
    dataset_path_1 = DatasetPath(1, "/galaxy/database/files/dataset_1.dat")
    assert dataset_path_1.dataset_id == 1
    assert dataset_path_1.real_path == "/galaxy/database/files/dataset_1.dat"
    assert dataset_path_1.false_path is None
    assert dataset_path_1.mutable
    assert str(dataset_path_1) == "/galaxy/database/files/dataset_1.dat"

    dataset_path_2 = DatasetPath(
        2, "/galaxy/database/files/dataset_2.dat", false_path="/mnt/galaxyData/files/dataset_2.dat", mutable=False
    )
    assert dataset_path_2.dataset_id == 2
    assert dataset_path_2.real_path == "/galaxy/database/files/dataset_2.dat"
    assert dataset_path_2.false_path == "/mnt/galaxyData/files/dataset_2.dat"
    assert not dataset_path_2.mutable
    assert str(dataset_path_2) == "/mnt/galaxyData/files/dataset_2.dat"
