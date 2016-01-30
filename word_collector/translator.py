import json

from contextlib import closing
from copy import deepcopy
from urllib import request
from urllib.parse import quote


class Translator(object):
    """ Translates given German word to Russian via Yandex Dictionary.
    """

    REQUEST_TEMPLATE = 'https://dictionary.yandex.net/api/v1/dicservice.json/' \
                       'lookup?key={api_key}&lang=de-ru&text={text}'
    TRANSLATOR_KEY = 'dict.1.1.20151205T223338Z.19544f83c700c55e.' \
                     'ac63dc20e339b921135a0cd233e2c5135d58aacb'

    def __init__(self, api_key=TRANSLATOR_KEY):
        self.api_key = api_key

    @staticmethod
    def _prepare_examples(examples):
        """ Turns structured example response into a simple list or strings.
        Each example is formatted as FOREIGN_PHRASE — TRANSLATION
        """

        if not examples:
            return examples

        prepared_examples = []
        for example in examples:
            example = '%s — %s' % (example['text'], example['tr'][0]['text'])
            prepared_examples.append(example)

        return prepared_examples

    def translate(self, text):
        translate_request = self.REQUEST_TEMPLATE.format(
            api_key=self.api_key, text=quote(text, encoding='utf-8'))
        try:
            with closing(request.urlopen(translate_request)) as response:
                response = json.loads(response.read().decode('utf-8'))
                translation = response['def']
                if not translation:
                    return None
                else:
                    translation = translation[0]

                gender = translation.get('gen', None)
                type_ = translation.get('pos', None)
                original = translation.get('text', None)
                translations = translation.get('tr', [])
                translations = [
                    {'type': e['pos'],
                     'text': e['text'],
                     'example': Translator._prepare_examples(e.get('ex', None))}
                    for e in translations]
                return TranslatedWord(gender, type_, original, translations)
        except Exception as e:
            return e


class TranslatedWord(object):
    """ Data class to hold word and its translations.
    """

    def __init__(self, gender, type_, original, translations):
        self._gender = gender
        self._type = type_
        self._original = original
        self._translations = translations

    @property
    def gender(self):
        return self._gender

    @property
    def type(self):
        return self._type

    @property
    def original(self):
        return self._original

    @property
    def translations(self):
        return deepcopy(self._translations)

    def to_dict(self):
        """ Transforms instance to dictionary that can be serialized to tinydb.
        """

        return dict(
            gender=self.gender,
            type=self.type,
            original=self.original,
            translations=self.translations)
