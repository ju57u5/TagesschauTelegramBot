from telegram.ext import Updater, InlineQueryHandler, CommandHandler, PicklePersistence
from telegram.ext.filters import Filters
from telegram import InlineQueryResultVideo, InputTextMessageContent, ParseMode
import requests
import logging
import credentials
from lxml import etree

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

TAGESTHEMEN = "https://www.tagesschau.de/export/video-podcast/webs/tagesthemen_https/"
TAGESSCHAU = "https://www.tagesschau.de/export/video-podcast/webs/tagesschau_https/"
TAGESSCHAU_IN_100 = "https://www.tagesschau.de/export/video-podcast/webm/tagesschau-in-100-sekunden_https/"
CACHE_TIME = 10
bot_persistence = PicklePersistence(filename='bot_data', store_bot_data=True)
updater = Updater(credentials.key, persistence=bot_persistence, use_context=True)


def get_newest_episode(podcast_url, input_message_content=False):
    rss_response = requests.get(podcast_url)
    root = etree.fromstring(rss_response.content)
    channel = root.find("channel")
    item = channel.find("item")
    title = item.find("title").text
    enclosure = item.find("enclosure")
    url = enclosure.attrib["url"]
    mime_type = enclosure.attrib["type"]
    description = item.find("description").text
    uid = item.find("guid").text
    thumb = item.find("itunes:image", root.nsmap).attrib["href"]
    if not input_message_content:
        return [InlineQueryResultVideo(id=uid, video_url=url, mime_type=mime_type, thumb_url=thumb, title=title, caption=description, description=description)]
    else:
        content = InputTextMessageContent(f"{url}", parse_mode=ParseMode.MARKDOWN)
        return [InlineQueryResultVideo(input_message_content=content, id=uid, video_url=url, mime_type=mime_type, thumb_url=thumb, title=title, caption=description, description=description)]    

def inline_query_handler(update, context):
    query_text = update.inline_query.query
    query_id = update.inline_query.id

    if not query_text: 
        query_text = "all"

    logging.info(f"Query {query_text}")
    query_text = query_text.lower()

    answer = []
    if query_text == "tagesthemen" or query_text == "all":
        answer += get_newest_episode(TAGESTHEMEN, input_message_content=False)

    if query_text == "tagesschau" or query_text == "schau" or query_text == "all":
        answer += get_newest_episode(TAGESSCHAU, input_message_content=False)

    if query_text == "tagesschau100" or query_text == "100" or query_text == "all":
        answer += get_newest_episode(TAGESSCHAU_IN_100)

    if len(answer) > 0:
        logging.info(list(map(lambda x: x.video_url, answer)))
    context.bot.answer_inline_query(query_id, answer, cache_time=CACHE_TIME)

if __name__ == "__main__":
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query_handler))
    updater.start_polling()
    updater.idle()
