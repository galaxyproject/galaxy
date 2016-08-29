from bs4 import BeautifulSoup

import urllib
import re
import random


def get_latest_id():
    url = 'http://phdcomics.com/gradfeed.php'
    content = urllib.urlopen(url).read()
    soap = BeautifulSoup(content, 'html.parser')
    pattern = '(?:http://www\.phdcomics\.com/comics\.php\?f=)(\d+)'
    return max([
        int(re.search(pattern, link.text).group(1))
        for link in soap.find_all('link', text=re.compile(pattern))
    ])


def main(webhook):
    error = ''
    data = {}

    try:
        if 'latest_id' not in webhook.config.keys():
            webhook.config['latest_id'] = get_latest_id()

        random_id = random.randint(1, webhook.config['latest_id'])
        url = 'http://www.phdcomics.com/comics/archive.php?comicid=%d' % \
            random_id
        content = urllib.urlopen(url).read()
        soap = BeautifulSoup(content, 'html.parser')
        comics_src = soap.find_all('img', id='comic')[0].attrs.get('src')
        data = {'src': comics_src}

    except Exception as e:
        error = str(e)

    return {'success': not error, 'error': error, 'data': data}
