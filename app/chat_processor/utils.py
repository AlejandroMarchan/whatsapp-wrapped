import re
import base64
import zipfile
import tempfile
from datetime import datetime
from spacy.lang.es import Spanish
import pandas as pd
import logging

log = logging.getLogger(__name__)

nlp = Spanish()

STOPWORDS = []

with open('app/assets/stopwords-es.txt', 'r') as f:
    STOPWORDS = f.read().splitlines()

STOPWORDS += ['(', ')', '.', '"', "'", ',', ':', ';', '?', '¿', '¡', '!', 'º', 'ª', '%', '/', "\\", '*', '+', '-',
              '=', '#', '€', '-', '_', '\n', '&', '@', '[', ']', '>', '<', "'", '\t', '️']

# Pre-compile regex for efficiency
MESSAGE_REGEX = re.compile(
    r'\[(\d{1,2}\/\d{1,2}\/\d{1,2}, \d{1,2}:\d{2}:\d{2})\] (.+?): (.*)')

DISCARD_WORD_REGEXES = [
    # numbers
    re.compile(r'^\d+$'),
    # Messages that only contain j or a
    re.compile(r'^[ja]+$'),
]


def check_discard_word(word):
    for regex in DISCARD_WORD_REGEXES:
        if regex.match(word):
            return True

    return False


def get_words_df(chat_df):
    messages_df = chat_df[
        (chat_df['message'] != 'audio omitido') &
        (chat_df['message'] != 'sticker omitido') &
        (chat_df['message'] != 'Video omitido') &
        (chat_df['message'] != 'imagen omitida') &
        (chat_df['message'] != 'GIF omitido')
    ][['person', 'message']]

    wordle_words = [
        'https://wordle.danielfrg.com',
        'https://lapalabradeldia.com/',
        'Wordle',
        'HeardlEsp'
    ]

    words = []

    for row in messages_df.values:
        person = row[0]
        message = row[1]

        # Remove Wordle messages
        if any([word in message for word in wordle_words]):
            continue

        for token in nlp(message):
            word = token.text.lower().strip()

            word = word.replace('🏼', '')

            if word != '' and word not in STOPWORDS and not check_discard_word(word):
                words.append({
                    'person': person,
                    'word': word
                })

    words_df = pd.DataFrame(words)

    return words_df


def extract_messages_from_chat(file, chat_name):
    with tempfile.NamedTemporaryFile(suffix='.zip', delete=True) as temp:
        # Write the uploaded file content to a temporary zip file
        try:
            file = file.split('base64,')[1]
            temp.write(base64.b64decode(file))

            with zipfile.ZipFile(temp.name, 'r') as archive:
                chat = archive.read('_chat.txt').decode()

            return parse_messages_from_chat(chat, chat_name)

        except (ValueError, zipfile.BadZipFile) as e:
            log.error('Error while decoding and reading ZIP file:', e)
            return []

        except Exception as e:
            log.error('Unexpected error:', e)
            return []


def parse_messages_from_chat(chat, chat_name):
    messages = []
    try:
        for line in chat.split('\n'):
            # Remove LTR mark
            line = line.replace('‎', '').replace('\r', '')
            # Extract the date and time, sender name and message sent
            match = MESSAGE_REGEX.match(line)
            if match:
                date, person, message = match.groups()
                # Convert the date and time into a datetime object
                date = datetime.strptime(date, '%d/%m/%y, %H:%M:%S')
                if person != 'Tú' and person != chat_name and 'Los mensajes y las llamadas están cifrados de extremo a extremo. Nadie fuera de este chat, ni siquiera WhatsApp, puede leerlos ni escucharlos.' not in message:
                    messages.append({
                        'date': date,
                        'person': person,
                        'message': message
                    })
            elif len(messages) > 0:
                messages[-1]['message'] += ' ' + line
    except Exception as e:
        log.error('The following error happened wile parsing the chat: ', e)
    return messages
