import requests


def delete(api_key, url, data, return_formatted=True):
    """
    Sends an API DELETE request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    response = response.json()
    if return_formatted:
        print("Response")
        print("--------")
        print(response)
    else:
        return response


def display(url, api_key=None, return_formatted=True):
    """Sends an API GET request and acts as a generic formatter for the JSON response."""
    r = get(url, api_key=api_key)
    if not return_formatted:
        return r
    elif isinstance(r, list):
        # Response is a collection as defined in the REST style.
        print("Collection Members")
        print("------------------")
        for n, i in enumerate(r):
            # All collection members should have a name in the response.
            # url is optional
            if "url" in i:
                print("#{}: {}".format(n + 1, i.pop("url")))
            if "name" in i:
                print(f"  name: {i.pop('name')}")
            for k, v in i.items():
                print(f"  {k}: {v}")
        print()
        print(f"{len(r)} element(s) in collection")
    elif isinstance(r, dict):
        # Response is an element as defined in the REST style.
        print("Member Information")
        print("------------------")
        for k, v in r.items():
            print(f"{k}: {v}")
    else:
        print(f"response is unknown type: {type(r)}")


def get(url, api_key=None):
    """Do the GET."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def post(url, data, api_key=None):
    """Do the POST."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    response = requests.post(url, data, headers=headers)
    response.raise_for_status()
    return response.json()


def put(url, data, api_key=None):
    """Do the PUT."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    response = requests.put(url, data, headers=headers)
    response.raise_for_status()
    return response.json()


def submit(url, data, api_key=None, return_formatted=True):
    """
    Sends an API POST request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    response = post(url, data, api_key)
    if not return_formatted:
        return response
    print("Response")
    print("--------")
    if isinstance(response, list):
        # Currently the only implemented responses are lists of dicts, because submission creates
        # some number of collection elements.
        for i in response:
            if isinstance(i, dict):
                if "url" in i:
                    print(i.pop("url"))
                else:
                    print("----")
                if "name" in i:
                    print(f"  name: {i.pop('name')}")
                for k, v in i.items():
                    print(f"  {k}: {v}")
            else:
                print(i)
    else:
        print(response)


def update(api_key, url, data, return_formatted=True):
    """
    Sends an API PUT request and acts as a generic formatter for the JSON response.  The
    'data' will become the JSON payload read by the Tool Shed.
    """
    response = put(url, data, api_key=api_key)
    if return_formatted:
        print("Response")
        print("--------")
        print(response)
    else:
        return response
