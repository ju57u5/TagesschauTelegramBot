from telegram.ext import Updater, InlineQueryHandler, CommandHandler, PicklePersistence
from telegram.ext.filters import Filters
from telegram import InlineQueryResultVideo, InputTextMessageContent, ParseMode
import requests
import logging
import json
from lxml import etree

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

CACHE_TIME = 10
bot_persistence = PicklePersistence(filename='bot_data', store_bot_data=True)


"""
Configuration for the different show. Format:
{
    "keywords": List of all possible keywords, this this show should be found with.

    "quality": Dict of feeds for the different quality versions of this show. key: quality-identifier, value: feed-url.

    "default_quality": String with the default quality-indentifiert, that should be chosen if one isnt specified. 
                       This should preferably be a feed, that produces files < 20MB so that they can be shown in the video player.

    "input_message_content": If the video result should use input_message_content to just print the url. 
                             This should be set to true, if no feed can get under filesize < 20MB to allow basic functionality wihtout errors. 

}
"""
SHOW_CONFIG = [
    {
        "keywords": ["all", "tagesschau", "schau"],
        "quality": {
            "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/tagesschau_https/",
            "webl": "https://www.tagesschau.de/export/video-podcast/webl/tagesschau_https/",
            "webm": "https://www.tagesschau.de/export/video-podcast/webm/tagesschau_https/",
            "webs": "https://www.tagesschau.de/export/video-podcast/webs/tagesschau_https/",

        },
        "default_quality": "webs",
        "input_message_content": False,
    },
    {
        "keywords": ["all", "tagesthemen", "themen"],
        "quality": {
            "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/tagesthemen_https/",
            "webl": "https://www.tagesschau.de/export/video-podcast/webl/tagesthemen_https/",
            "webm": "https://www.tagesschau.de/export/video-podcast/webm/tagesthemen_https/",
            "webs": "https://www.tagesschau.de/export/video-podcast/webs/tagesthemen_https/",
            "yt": "https://www.youtube.com/feeds/videos.xml?channel_id=UC5NOEUbkLheQcaaRldYW5GA"

        },
        "default_quality": "yt",
        "input_message_content": True,
    },
    {
        "keywords": ["all", "tagesschau100", "schau100", "100"],
        "quality": {
            "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/tagesschau-in-100-sekunden_https/",
            "webl": "https://www.tagesschau.de/export/video-podcast/webl/tagesschau-in-100-sekunden_https/",
            "webm": "https://www.tagesschau.de/export/video-podcast/webm/tagesschau-in-100-sekunden_https/",
            "webs": "https://www.tagesschau.de/export/video-podcast/webs/tagesschau-in-100-sekunden_https/",

        },
        "default_quality": "webm",
        "input_message_content": False,
    },
]

with open("credentials.json") as config:
    key = json.load(config)["key"]
    updater = Updater(key, persistence=bot_persistence, use_context=True)


def get_newest_episode_from_podcast_feed(podcast_url, input_message_content=False):
    rss_response = requests.get(podcast_url)
    root = etree.fromstring(rss_response.content)
    
    channel = root.find("channel")
    item = channel.find("item")
    title = item.find("title").text
    description = item.find("description").text
    uid = item.find("guid").text
    thumb = item.find("itunes:image", root.nsmap).attrib["href"]

    enclosure = item.find("enclosure")
    url = enclosure.attrib["url"]
    mime_type = enclosure.attrib["type"]
    
    
    if not input_message_content:
        return [InlineQueryResultVideo(id=uid, video_url=url, mime_type=mime_type, thumb_url=thumb, title=title, caption=description, description=description)]
    else:
        content = InputTextMessageContent(
            f"{url}", parse_mode=ParseMode.MARKDOWN)
        return [InlineQueryResultVideo(input_message_content=content, id=uid, video_url=url, mime_type=mime_type, thumb_url=thumb, title=title, caption=description, description=description)]

def get_newest_episode_from_yt_feed(yt_url):
    rss_response = requests.get(yt_url)
    root = etree.fromstring(rss_response.content)
    entries = root.findall("entry", root.nsmap)

    for entry in entries:
        vid_title = entry.find("title", entry.nsmap)
        if("tagesthemen" in vid_title.text.lower()):
            media = entry.find("media:group", entry.nsmap)
            uid = entry.find("yt:videoId", entry.nsmap).text
            title = vid_title.text
            thumb = media.find("media:thumbnail", media.nsmap).attrib["url"]
            description = media.find("media:description", media.nsmap).text
            url = entry.find("link", entry.nsmap).attrib["href"]
  
            content = InputTextMessageContent(
                f"{url}", parse_mode=ParseMode.MARKDOWN)
            return [InlineQueryResultVideo(input_message_content=content, id=uid, video_url=url, mime_type="text/html", thumb_url=thumb, title=title, caption=description, description=description)]

def inline_query_handler(update, context):
    query_text = update.inline_query.query
    query_id = update.inline_query.id

    if not query_text:
        query_text = "all"

    logging.info(f"Query {query_text}")
    query_text = query_text.lower()
    query_args = query_text.split()

    keyword = query_args[0]
    quality = query_args[1] if len(query_args) > 1 else None
    input_message_content_parameter = query_args[2] if len(
        query_args) > 2 else None
    answer = []

    for show in SHOW_CONFIG:
        if keyword in show["keywords"]:
            if quality:
                try:
                    feed = show["quality"][quality]
                except KeyError:
                    continue
            else:
                default_quality = show["default_quality"]
                feed = show["quality"][default_quality]

            if input_message_content_parameter != None:
                input_message_content = input_message_content_parameter.lower() in [
                    "true", "1", "yes"]
            else:
                input_message_content = show["input_message_content"]

            if(quality == "yt"):
                answer += get_newest_episode_from_yt_feed(feed)
            else:
                answer += get_newest_episode_from_podcast_feed(
                    feed, input_message_content)

    if len(answer) > 0:
        logging.info(list(map(lambda x: x.video_url, answer)))
    context.bot.answer_inline_query(query_id, answer, cache_time=CACHE_TIME)

if __name__ == "__main__":
    updater.dispatcher.add_handler(InlineQueryHandler(inline_query_handler))
    updater.start_polling()
    updater.idle()
