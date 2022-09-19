from galaxy.tool_util.deps.container_volumes import DockerVolume


def test_docker_volume_valid():
    volume_string = "/a:/b:ro"
    docker_volume = DockerVolume.from_str(volume_string)
    assert docker_volume.mode_is_valid
    assert str(docker_volume) == volume_string


def test_docker_volume_valid_host_path_only():
    docker_volume = DockerVolume.from_str("/a:ro")
    assert docker_volume.mode_is_valid
    assert str(docker_volume) == "/a:/a:ro"


def test_docker_volume_not_valid():
    docker_volume = DockerVolume.from_str("/a:/b")
    assert not docker_volume.mode_is_valid
