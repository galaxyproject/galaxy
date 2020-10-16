import argparse
import json

import requests
import yaml


def main():
    parser = argparse.ArgumentParser(description='Upload a directory into a data library')
    parser.add_argument("-u", "--url", dest="url", required=True, help="Galaxy URL")
    parser.add_argument("-a", "--api", dest="api_key", required=True, help="API Key")
    parser.add_argument('target', metavar='FILE', type=str,
                        help='file describing data library to fetch')
    args = parser.parse_args()
    with open(args.target, "r") as f:
        target = yaml.load(f)

    histories_url = args.url + "/api/histories"
    new_history_response = requests.post(histories_url, data={'key': args.api_key})

    fetch_url = args.url + '/api/tools/fetch'
    payload = {
        'key': args.api_key,
        'targets': json.dumps([target]),
        'history_id': new_history_response.json()["id"]
    }

    response = requests.post(fetch_url, data=payload)
    print(response.content)


if __name__ == '__main__':
    main()
