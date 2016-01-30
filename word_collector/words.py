from datetime import datetime
from collections import Counter
from contextlib import closing
from re import findall
from re import split
from re import sub
from urllib import request

from word_collector.translator import Translator
from jinja2 import Environment, PackageLoader
from lxml import etree
from lxml import html

from word_collector.storage import Database
from word_collector import create_logger

SPIEGEL_RSS = 'http://www.spiegel.de/schlagzeilen/tops/index.rss'
NUMBER_OF_TOP_WORDS = 100
log = create_logger(__name__)


class ArticleExtractor(object):
    pass

def list_article_urls():
    """ This method lists urls in an rss feed.
    Returns:

    """
    with closing(request.urlopen(SPIEGEL_RSS)) as response:
        log.info('Getting urls for %s', SPIEGEL_RSS)
        root = etree.fromstring(response.read())
        return root.xpath('//item/link/text()')


def get_article_lines(url):
    with closing(request.urlopen(url)) as response:
        log.info('Getting content of an article %s', url)
        root = html.document_fromstring(response.read())
        # Xpath returns a set of nodes, from which we need just first one.
        try:
            article_node = root.xpath(
                '//div[@id="js-article-column"]/'
                'div[contains(@class, "article-section")]')[0]
        except Exception:
            log.warning('Could not get content of an article %s', url)
            return []

        meaningful_lines = []
        # When iterating over element's lines we'll get a bunch of empty ones,
        # js code and comments. We want to filter them out.
        for text in article_node.itertext():
            # Blocks of text which start with \r\n\t or \n\t usually contains
            # code. Also avoid lines with TAB and lines with space chars only.
            if not (text.startswith('\r\n\t') or text.startswith('\n\t')) \
                    and text.lstrip() and 'TAB' not in text:
                meaningful_lines.append(text)

        # Strip last two lines as they always contains code.
        return meaningful_lines[:-2]


def get_article_words(lines):
    word_counter = Counter()

    for line in lines:
        for word in (w.lower() for w in split(r'[\s\.,\(\)]', line) if w):
            # Remove all words with digits
            if findall(r'\d', word):
                continue
            # Remove html_ parts that were not trimmed before
            if 'html_' in word:
                continue
            # Remove single letter words that makes not sense in German
            if len(word) <= 1:
                continue

            word = sub('[^\w]', '', word)
            word_counter[word] += 1

    return word_counter


def main():
    db = Database('db.json')
    today = datetime.now().strftime('%d/%m/%Y')

    yt = Translator()
    main_counter = Counter()
    for url in list_article_urls():
        lines = get_article_lines(url)
        log.info('Got %d lines for %s', len(lines), url)
        words = get_article_words(lines)
        log.info('Got %d unique words for %s', len(words.items()), url)
        main_counter.update(words)

    # List words along with number of times they encountered in rss articles
    for word, count in main_counter.most_common(n=NUMBER_OF_TOP_WORDS):
        db.insert_translation(word, yt.translate)
        db.insert_or_update_counter(count, word, today)

    top = db.get_top_words_of_the_day(today, type='noun', n=10)
    env = Environment(loader=PackageLoader('word_collector', 'templates'))
    template = env.get_template('top_nouns.html')
    with open('top_nouns.html', 'w', encoding='utf-8') as file:
        file.write(template.render(tops=top, date=today))
        
if __name__ == '__main__':
    main()
