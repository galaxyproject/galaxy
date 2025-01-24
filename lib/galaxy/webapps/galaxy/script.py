import os
from argparse import ArgumentParser

import uvicorn


def main() -> None:
    parser = ArgumentParser(
        prog="galaxy-web",
        description="Run Galaxy Web Server",
    )
    parser.add_argument("--config", "-c", help="Galaxy config file")
    parser.add_argument("--single-user", "-s", help="Single user mode as user SINGLE_USER")
    parser.add_argument("--bind", "-b", default="localhost:8080", help="Bind to <host>:<port>")
    parser.add_argument(
        "--client-path", "-n", default="node_modules/@galaxyproject/galaxy-client", help="Path to Galaxy client"
    )
    args = parser.parse_args()
    if args.config:
        os.environ["GALAXY_CONFIG_FILE"] = args.config
    if args.single_user:
        os.environ["GALAXY_CONFIG_SINGLE_USER"] = args.single_user
        os.environ["GALAXY_CONFIG_ADMIN_USERS"] = args.single_user
    os.environ["GALAXY_CONFIG_STATIC_DIR"] = args.client_path
    uvicorn.run(
        "galaxy.webapps.galaxy.fast_factory:factory",
        factory=True,
        host=args.bind.split(":")[0],
        port=int(args.bind.split(":")[1]),
    )
