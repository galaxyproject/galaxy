#!/usr/bin/env python

import argparse
import json
import logging
import sys
import tempfile
from typing import (
    Dict,
    List,
)

import requests

from galaxy.tool_util.deps.conda_util import CondaContext
from galaxy.util import (
    check_github_api_response_rate_limit,
    which,
)
from .mulled_list import get_singularity_containers
from .util import (
    build_target,
    MULLED_SOCKET_TIMEOUT,
    v2_image_name,
)

try:
    from whoosh.fields import (
        Schema,
        STORED,
        TEXT,
    )
    from whoosh.index import create_in
    from whoosh.qparser import QueryParser
except ImportError:
    Schema = TEXT = STORED = create_in = QueryParser = None

QUAY_API_URL = "https://quay.io/api/v1/repository"
conda_path = which("conda")


class QuaySearch:
    """
    Tool to search within a quay organization for a given software name.
    """

    def __init__(self, organization):
        self.index = None
        self.organization = organization

    def build_index(self):
        """
        Create an index to quickly examine the repositories of a given quay.io organization.
        """
        # download all information about the repositories from the
        # given organization in self.organization

        parameters = {"public": "true", "namespace": self.organization}
        r = requests.get(
            QUAY_API_URL, headers={"Accept-encoding": "gzip"}, params=parameters, timeout=MULLED_SOCKET_TIMEOUT
        )
        tmp_dir = tempfile.mkdtemp()
        schema = Schema(title=TEXT(stored=True), content=STORED)
        self.index = create_in(tmp_dir, schema)

        json_decoder = json.JSONDecoder()
        decoded_request = json_decoder.decode(r.text)
        writer = self.index.writer()
        for repository in decoded_request["repositories"]:
            writer.add_document(title=repository["name"], content=repository["description"])
        writer.commit()

    def search_repository(self, search_string, non_strict):
        """
        Search Docker containers on quay.io.
        Results are displayed with all available versions,
        including the complete image name.
        """
        # with statement closes searcher after usage.
        with self.index.searcher() as searcher:
            query = QueryParser("title", self.index.schema).parse(search_string)
            results = searcher.search(query)
            if non_strict:
                # look for spelling errors and use suggestions as a search term too
                corrector = searcher.corrector("title")
                suggestions = corrector.suggest(search_string, limit=2)

                # get all repositories with suggested keywords
                for suggestion in suggestions:
                    search_string = f"*{suggestion}*"
                    query = QueryParser("title", self.index.schema).parse(search_string)
                    results_tmp = searcher.search(query)
                    results.extend(results_tmp)

            out = list()

            for result in results:
                title = result["title"]
                for version in self.get_additional_repository_information(title):
                    out.append(
                        {
                            "package": title,
                            "version": version,
                        }
                    )

            return out

    def get_additional_repository_information(self, repository_string):
        """
        Function downloads additional information from quay.io to
        get the tag-field which includes the version number.
        """
        url = f"{QUAY_API_URL}/{self.organization}/{repository_string}"
        r = requests.get(url, headers={"Accept-encoding": "gzip"}, timeout=MULLED_SOCKET_TIMEOUT)

        json_decoder = json.JSONDecoder()
        decoded_request = json_decoder.decode(r.text)
        return decoded_request["tags"]


class CondaSearch:
    """
    Tool to search the bioconda channel
    """

    def __init__(self, channel):
        self.channel = channel

    def get_json(self, search_string) -> List[Dict[str, str]]:
        """
        Function takes search_string variable and returns results from the bioconda channel in JSON format

        """
        if not conda_path:
            raise Exception("Invalid search destination. Required dependency [conda] is not in your PATH.")
        try:
            conda_context = CondaContext(conda_exec=conda_path, ensure_channels=self.channel)
            raw_out = conda_context.exec_search([search_string])
        except Exception as e:
            logging.info(f"Search failed with: {e}")
            return []
        header_found = False
        lines_fields: List[List[str]] = []
        for line in raw_out.splitlines():
            if line.startswith("#"):
                header_found = True
            elif header_found:
                lines_fields.append(line.split())
        return [
            {"package": line_fields[0], "version": line_fields[1], "build": line_fields[2]} for line_fields in lines_fields
        ]


class GitHubSearch:
    """
    Tool to search the GitHub bioconda-recipes repo
    """

    def get_json(self, search_string):
        """
        Takes search_string variable and return results from the bioconda-recipes github repository in JSON format

        DEPRECATED: this method is currently unreliable because the API query
        sometimes succeeds but returns no items.
        """
        response = requests.get(
            f"https://api.github.com/search/code?q={search_string}+in:path+repo:bioconda/bioconda-recipes+path:recipes",
            timeout=MULLED_SOCKET_TIMEOUT,
        )
        check_github_api_response_rate_limit(response)
        response.raise_for_status()
        return response.json()

    def process_json(self, json_response, search_string):
        """
        Take JSON input and process it, returning the required data
        """
        top_10_items = json_response["items"][0:10]  # get top ten results
        return [{"name": result["name"], "path": result["path"]} for result in top_10_items]

    def recipe_present(self, search_string):
        """
        Check if a recipe exists in bioconda-recipes which matches search_string exactly
        """
        response = requests.get(
            f"https://api.github.com/repos/bioconda/bioconda-recipes/contents/recipes/{search_string}",
            timeout=MULLED_SOCKET_TIMEOUT,
        )
        check_github_api_response_rate_limit(response)
        return response.status_code == 200


def get_package_hash(packages, versions):
    """
    Take packages and versions (if the latter are given) and returns a hash for each. Also checks github to see if the container is already present.
    """
    hash_results = {}
    targets = []
    if versions:
        for p in packages:
            targets.append(build_target(p, version=versions[p]))
    else:  # if versions are not given only calculate the package hash
        for p in packages:
            targets.append(build_target(p))
    # make the hash from the processed targets
    package_hash = v2_image_name(targets)
    hash_results["package_hash"] = package_hash.split(":")[0]
    if versions:
        hash_results["version_hash"] = package_hash.split(":")[1]

    r = requests.get(
        f"https://quay.io/api/v1/repository/biocontainers/{hash_results['package_hash']}", timeout=MULLED_SOCKET_TIMEOUT
    )
    if r.status_code == 200:
        hash_results["container_present"] = True
        if versions:  # now test if the version hash is listed in the repository tags
            # remove -0, -1, etc from end of the tag
            tags = [n[:-2] for n in r.json()["tags"]]
            if hash_results["version_hash"] in tags:
                hash_results["container_present_with_version"] = True
            else:
                hash_results["container_present_with_version"] = False
    else:
        hash_results["container_present"] = False
    return hash_results


def singularity_search(search_string):
    """
    Check if a singularity package is present and return the link.
    """
    results = []

    containers = get_singularity_containers()

    for container in containers:
        if search_string in container:
            name = container.split(":")[0]
            version = container.split(":")[1]
            results.append({"package": name, "version": version})

    return results


def readable_output(json, organization="biocontainers", channel="bioconda"):
    # if json is empty:
    if sum(len(json[destination][results]) for destination in json for results in json[destination]) == 0:
        sys.stdout.write("No results found for that query.\n")
        return

    # return results for quay, conda and singularity together
    if (
        sum(
            len(json[destination][results])
            for destination in [
                "quay",
                "conda",
                "singularity",
            ]
            for results in json.get(destination, [])
        )
        > 0
    ):
        sys.stdout.write("The query returned the following result(s).\n")
        # put quay, conda etc results as lists in lines
        lines = [["LOCATION", "NAME", "VERSION", "COMMAND\n"]]
        for results in json.get("quay", {}).values():
            for result in results:
                lines.append(
                    [
                        "quay",
                        result["package"],
                        result["version"],
                        f"docker pull quay.io/{organization}/{result['package']}:{result['version']}\n",
                    ]
                )  # NOT a real solution
        for results in json.get("conda", {}).values():
            for result in results:
                lines.append(
                    [
                        "conda",
                        result["package"],
                        f"{result['version']}--{result['build']}",
                        f"conda install -c {channel} {result['package']}={result['version']}={result['build']}\n",
                    ]
                )
        for results in json.get("singularity", {}).values():
            for result in results:
                lines.append(
                    [
                        "singularity",
                        result["package"],
                        result["version"],
                        f"wget https://depot.galaxyproject.org/singularity/{result['package']}:{result['version']}\n",
                    ]
                )

        col_width0, col_width1, col_width2 = (
            max(len(line[n]) for line in lines) + 2 for n in (0, 1, 2)
        )  # def max col widths for the output

        # create table
        for line in lines:
            sys.stdout.write(
                "".join((line[0].ljust(col_width0), line[1].ljust(col_width1), line[2].ljust(col_width2), line[3]))
            )  # output

    if json.get("github_recipe_present", False):
        sys.stdout.write("\n" if "lines" in locals() else "")
        sys.stdout.write(
            "The following recipes were found in the bioconda-recipes repository which exactly matched one of the search terms:\n"
        )
        lines = [["QUERY", "LOCATION\n"]]
        for recipe in json["github_recipe_present"]["recipes"]:
            lines.append(
                [recipe, f"https://api.github.com/repos/bioconda/bioconda-recipes/contents/recipes/{recipe}\n"]
            )

        col_width0 = max(len(line[0]) for line in lines) + 2

        for line in lines:
            sys.stdout.write("".join((line[0].ljust(col_width0), line[1])))  # output

    if sum(len(json["github"][results]) for results in json.get("github", [])) > 0:
        sys.stdout.write("\n" if "lines" in locals() else "")
        sys.stdout.write("Other result(s) on the bioconda-recipes GitHub repository:\n")
        lines = [["QUERY", "FILE", "URL\n"]]
        for search_string, results in json.get("github", {}).items():
            for result in results:
                lines.append(
                    [
                        search_string,
                        result["name"],
                        f"https://github.com/bioconda/bioconda-recipes/tree/master/{result['path']}\n",
                    ]
                )

        # def max col widths for the output
        col_width0, col_width1 = (max(len(line[n]) for line in lines) + 2 for n in (0, 1))

        for line in lines:
            sys.stdout.write("".join((line[0].ljust(col_width0), line[1].ljust(col_width1), line[2])))  # output


def deps_error_message(package):
    return f"Required dependency [{package}] is not installed. Run 'pip install galaxy-tool-util[mulled]'."


def main(argv=None):
    if Schema is None:
        sys.stdout.write(deps_error_message("Whoosh"))
        return

    destination_defaults = ["quay", "singularity", "github"]
    if conda_path:
        destination_defaults.append("conda")

    parser = argparse.ArgumentParser(description="Searches in a given quay organization for a repository")
    parser.add_argument(
        "-d",
        "--destination",
        dest="search_dest",
        nargs="+",
        default=destination_defaults,
        help="Choose where to search. Options are 'conda', 'quay', 'singularity' and 'github'. If no option are given, all will be searched.",
    )
    parser.add_argument(
        "-o",
        "--organization",
        dest="organization_string",
        default="biocontainers",
        help="Change quay organization to search; default is biocontainers.",
    )
    parser.add_argument(
        "-c",
        "--channel",
        dest="channel_string",
        default="bioconda",
        help="Change conda channels to search; default is bioconda.",
    )
    parser.add_argument(
        "--non-strict",
        dest="non_strict",
        action="store_true",
        help="Autocorrection of typos activated. Lists more results but can be confusing.\
                        For too many queries quay.io blocks the request and the results can be incomplete.",
    )
    parser.add_argument("-j", "--json", dest="json", action="store_true", help="Returns results as JSON.")
    parser.add_argument("-s", "--search", required=True, nargs="+", help="The name of the tool(s) to search for.")

    args = parser.parse_args()
    json_results = {dest: {} for dest in args.search_dest}
    versions = {}

    if len(args.search) > 1:  # get hash if multiple packages are searched
        args.search.append(get_package_hash(args.search, versions)["package_hash"])

    if "conda" in args.search_dest:
        conda_results = {}
        conda = CondaSearch(args.channel_string)

        for item in args.search:
            conda_results[item] = conda.get_json(item)
        json_results["conda"] = conda_results

    if "github" in args.search_dest:
        github_results = {}
        github_recipe_present = []
        github = GitHubSearch()

        for item in args.search:
            if github.recipe_present(item):
                github_recipe_present.append(item)
            else:
                github_json = github.get_json(item)
                github_results[item] = github.process_json(github_json, item)

        json_results["github"] = github_results
        json_results["github_recipe_present"] = {"recipes": github_recipe_present}

    if "quay" in args.search_dest:
        quay_results = {}
        quay = QuaySearch(args.organization_string)
        quay.build_index()

        for item in args.search:
            quay_results[item] = quay.search_repository(item, args.non_strict)

        json_results["quay"] = quay_results

    if "singularity" in args.search_dest:
        singularity_results = {}
        for item in args.search:
            singularity_results[item] = singularity_search(item)
        json_results["singularity"] = singularity_results

    if args.json:
        print(json_results)
    else:
        readable_output(json_results, args.organization_string, args.channel_string)


__all__ = ("main",)


if __name__ == "__main__":
    main()
