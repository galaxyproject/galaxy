import urllib
import re
import random
import logging

log = logging.getLogger(__name__)


def main(trans, webhook):
    error = ''
    data = {}

    try:
        # Third-party dependencies
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            log.exception(e)
            return {}

        # Get latest id
        if 'latest_id' not in webhook.config.keys():
            url = 'http://phdcomics.com/gradfeed.php'
            content = urllib.urlopen(url).read()
            soap = BeautifulSoup(content, 'html.parser')
            pattern = '(?:http://www\.phdcomics\.com/comics\.php\?f=)(\d+)'
            webhook.config['latest_id'] = max([
                int(re.search(pattern, link.text).group(1))
                for link in soap.find_all('link', text=re.compile(pattern))
            ])

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
