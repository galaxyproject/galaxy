import galaxy.containers
import galaxy.containers.docker_model


def test_dummy():
    t = galaxy.containers.parse_containers_config('')
    assert t == {'_default_': {'type': 'docker'}}
    s = galaxy.containers.docker_model.DockerAttributeContainer()
    assert s.members == frozenset()
