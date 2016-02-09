from tinydb import JSONStorage
from tinydb import Query
from tinydb import TinyDB
from tinydb import where
from tinydb.storages import touch
from itertools import islice
from word_collector import create_logger

log = create_logger(__name__)


class Database(object):

    def __init__(self, db_path):
        self.db = TinyDB(db_path, storage=UnicodeJSONStorage)
        # Words that were already translated.
        self.already_translated = self.db.search(
                where('translation') != None)
        # Words that were attempted to translate but failed.
        self.non_translated = self.db.search(
                where('translation') == None)

    def _word_already_translated(self, word):
        for cached_word in self.already_translated:
            if word == cached_word['original']:
                return True
        for cached_word in self.non_translated:
            if word == cached_word['original']:
                return True

    def insert_translation(self, original, translation_func):
        if not self._word_already_translated(original):
            log.info('Inserting translation for %s into db', original)
            translation = translation_func(original)
            self.db.insert({
                'original': original,
                'translation': translation.to_dict() if translation else None})

    def insert_or_update_counter(self, count, original, date_str):
        counter = {'count': count, 'original': original, 'date': date_str}
        if self.db.search(
                (where('date') == date_str) & (where('original') == original)):
            log.info('Updating counter for %s into db', original)
            self.db.update(counter, where('date') == date_str)
        else:
            log.info('Inserting counter for %s into db', original)
            self.db.insert(counter)

    def get_top_words_of_the_day(self, date_str, type=None, n=10):
        query = Query()
        counters = self.db.search(query.date == date_str)
        for counter in counters:
            query = Query()
            result = self.db.search(
                (query.original == counter['original'])
                & query.translation.exists())
            if result:
                # There will be only one translation in database
                counter['translation'] = result[0]['translation']
            else:
                # This is unlikely to happen
                counter['translation'] = None

        sorted_counters = \
            sorted(counters, key=lambda x: x['count'], reverse=True)
        sorted_counters = \
            filter(lambda x: x['translation'], sorted_counters)
        if type:
            sorted_counters = \
                filter(
                    lambda x: x['translation']['type'] == type,
                    sorted_counters)

        return islice(sorted_counters, n)


class UnicodeJSONStorage(JSONStorage):
    """JSONStorage implementation that supports UTF-8 encoded content.
    """

    def read(self):
        return super(UnicodeJSONStorage, self).read()

    def write(self, data):
        super(UnicodeJSONStorage, self).write(data)

    def __init__(self, path, **kwargs):
        touch(path)  # Create file if not exists
        self.kwargs = dict(kwargs, **{'ensure_ascii': False})
        self._handle = open(path, 'r+', encoding='utf-8')
