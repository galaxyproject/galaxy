#!/usr/bin/env python

import argparse
import json
import sys
import tempfile

try:
    import requests
except ImportError:
    requests = None

try:
    from whoosh.fields import Schema
    from whoosh.fields import TEXT
    from whoosh.fields import STORED
    from whoosh.index import create_in
    from whoosh.qparser import QueryParser
except ImportError:
    Schema = TEXT = STORED = create_in = QueryParser = None

QUAY_API_URL = 'https://quay.io/api/v1/repository'


class QuaySearch():
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

        parameters = {'public': 'true', 'namespace': self.organization}
        r = requests.get(QUAY_API_URL, headers={'Accept-encoding': 'gzip'}, params=parameters,
                         timeout=12)

        tmp_dir = tempfile.mkdtemp()
        schema = Schema(title=TEXT(stored=True), content=STORED)
        self.index = create_in(tmp_dir, schema)

        json_decoder = json.JSONDecoder()
        decoded_request = json_decoder.decode(r.text)
        writer = self.index.writer()
        for repository in decoded_request['repositories']:
            writer.add_document(title=repository['name'], content=repository['description'])
        writer.commit()

    def search_repository(self, search_string, non_strict):
        """
        Search Docker containers on quay.io.
        Results are displayed with all available versions,
        including the complete image name.
        """
        # with statement closes searcher after usage.
        with self.index.searcher() as searcher:
            search_string = "*%s*" % search_string
            query = QueryParser("title", self.index.schema).parse(search_string)
            results = searcher.search(query)
            if non_strict:
                # look for spelling errors and use suggestions as a search term too
                corrector = searcher.corrector("title")
                suggestions = corrector.suggest(search_string, limit=2)

                # get all repositories with suggested keywords
                for suggestion in suggestions:
                    search_string = "*%s*" % suggestion
                    query = QueryParser("title", self.index.schema).parse(search_string)
                    results_tmp = searcher.search(query)
                    results.extend(results_tmp)

            sys.stdout.write("The query \033[1m %s \033[0m resulted in %s result(s).\n" % (search_string, len(results)))

            if non_strict:
                sys.stdout.write('The search was relaxed and the following search terms were searched: ')
                sys.stdout.write('\033[1m %s \033[0m\n' % ', '.join(suggestions))

            out = list()
            for result in results:
                title = result['title']
                for version in self.get_additional_repository_information(title):
                    row = [title]
                    row.append(version)
                    out.append(row)
            if out:
                col_width = max(len(word) for row in out for word in row) + 2  # padding
                for row in out:
                    name = row[0]
                    version = row[1]
                    sys.stdout.write("".join(word.ljust(col_width) for word in row) + "docker pull quay.io/%s/%s:%s\n" % (self.organization, name, version))
            else:
                sys.stdout.write("No results found for %s in quay.io/%s.\n" % (search_string, self.organization))

    def get_additional_repository_information(self, repository_string):
        """
        Function downloads additional information from quay.io to
        get the tag-field which includes the version number.
        """
        url = "%s/%s/%s" % (QUAY_API_URL, self.organization, repository_string)
        r = requests.get(url, headers={'Accept-encoding': 'gzip'}, timeout=12)

        json_decoder = json.JSONDecoder()
        decoded_request = json_decoder.decode(r.text)
        return decoded_request['tags']


def main(argv=None):
    parser = argparse.ArgumentParser(description='Searches in a given quay organization for a repository')
    parser.add_argument('-o', '--organization', dest='organization_string', default="biocontainers",
                        help='Change organization. Default is biocontainers.')
    parser.add_argument('--non-strict', dest='non_strict', action="store_true",
                        help='Autocorrection of typos activated. Lists more results but can be confusing.\
                        For too many queries quay.io blocks the request and the results can be incomplete.')
    parser.add_argument('-s', '--search', required=True,
                        help='The name of the tool you want to search for.')
    args = parser.parse_args()

    quay = QuaySearch(args.organization_string)
    quay.build_index()

    quay.search_repository(args.search, args.non_strict)


if __name__ == "__main__":
    main()
