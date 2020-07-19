"""
TagesschauTelegramBot

Share the current episode of Tagesschau/Tagesthemen with a quick inline command.
"""
import logging
import json
import requests
from telegram.ext import Updater, InlineQueryHandler, PicklePersistence
from telegram import InlineQueryResultVideo, InputTextMessageContent, ParseMode
from lxml import etree

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

CACHE_TIME = 10
SHOW_CONFIG = get_config()


def get_newest_episode_from_podcast_feed(podcast_url, input_message_content=False):
    """
    Get the newest episode from the podcast feed and return a list of InlineQueryResultVideos
    with the only member containing that episode.

    Keyword arguments:
    podcast_url (str): URL of the podcast where the episode should be taken from. The podcast must order its items from
                       most recent to oldest, because the first item is picked without any time comparisons.
    input_message_content (bool): Set the optional parameter input_message_content if the result should only contain a link.
                                  This is important if the podcast file is bigger than 20 MB because the response will fail.
    """
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
        return [
            InlineQueryResultVideo(
                id=uid,
                video_url=url,
                mime_type=mime_type,
                thumb_url=thumb,
                title=title,
                caption=description,
                description=description,
            )
        ]

    content = InputTextMessageContent(f"{url}", parse_mode=ParseMode.MARKDOWN)
    return [
        InlineQueryResultVideo(
            input_message_content=content,
            id=uid,
            video_url=url,
            mime_type=mime_type,
            thumb_url=thumb,
            title=title,
            caption=description,
            description=description,
        )
    ]


def get_newest_episode_from_yt_feed(yt_url):
    """
    Get the newest episode from the yt feed with a specific title and return a list of
    InlineQueryResultVideos with the only member containing that episode.

    Keyword arguments:
    yt_url (str): URL of the youtube atom feed where the episode should be taken from. The episode
                  will be filterd out based on the title.
    """
    rss_response = requests.get(yt_url)
    root = etree.fromstring(rss_response.content)
    entries = root.findall("entry", root.nsmap)

    for entry in entries:
        vid_title = entry.find("title", entry.nsmap)
        if "tagesthemen" in vid_title.text.lower():
            media = entry.find("media:group", entry.nsmap)
            uid = entry.find("yt:videoId", entry.nsmap).text
            title = vid_title.text
            thumb = media.find("media:thumbnail", media.nsmap).attrib["url"]
            description = media.find("media:description", media.nsmap).text
            url = entry.find("link", entry.nsmap).attrib["href"]

            content = InputTextMessageContent(f"{url}", parse_mode=ParseMode.MARKDOWN)
            return [
                InlineQueryResultVideo(
                    input_message_content=content,
                    id=uid,
                    video_url=url,
                    mime_type="text/html",
                    thumb_url=thumb,
                    title=title,
                    caption=description,
                    description=description,
                )
            ]
    return []


def inline_query_handler(update, context):
    """
    Inline query handler for the bot. Returns the appropriate shows as a result.

    query_text must be in the space seperated argument form: <keyword> <quality> <send-link>. Check the README for more information.
    """
    query_text = update.inline_query.query
    query_id = update.inline_query.id

    if not query_text:
        query_text = "all"

    logging.info("Query %s", query_text)
    query_text = query_text.lower()
    query_args = query_text.split()

    keyword_arg = query_args[0]
    quality_arg = query_args[1] if len(query_args) > 1 else None
    input_message_content_arg = query_args[2] if len(query_args) > 2 else None
    answer = []

    for show in SHOW_CONFIG:
        if keyword_arg in show["keywords"]:
            if quality_arg:
                try:
                    quality = quality_arg
                    feed = show["quality"][quality]
                except KeyError:
                    continue
            else:
                quality = show["default_quality"]
                feed = show["quality"][quality]

            if input_message_content_arg is not None:
                input_message_content = input_message_content_arg.lower() in [
                    "true",
                    "1",
                    "yes",
                ]
            else:
                input_message_content = show["input_message_content"]

            if quality == "yt":
                answer += get_newest_episode_from_yt_feed(feed)
            else:
                answer += get_newest_episode_from_podcast_feed(
                    feed, input_message_content
                )

    if len(answer) > 0:
        logging.info(list(map(lambda x: x.video_url, answer)))
    context.bot.answer_inline_query(query_id, answer, cache_time=CACHE_TIME)


def get_config():
    """
    Configuration for the different show. Format:
    {
        "keywords": List of all possible keywords, this this show should be found with.

        "quality": Dict of feeds for the different quality versions of this show. key:
                quality-identifier, value: feed-url.

        "default_quality": String with the default quality-indentifiert, that should be
                        chosen if one isnt specified. This should preferably be a feed,
                        that produces files < 20MB so that they can be shown in the video player.

        "input_message_content": If the video result should use input_message_content to just print
                                the url.
                                This should be set to true, if no feed can get under filesize < 20MB to
                                allow basic functionality wihtout errors.

    }
    """
    # pylint: disable=C0301
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
                "yt": "https://www.youtube.com/feeds/videos.xml?channel_id=UC5NOEUbkLheQcaaRldYW5GA",
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
            },
            "default_quality": "webm",
            "input_message_content": False,
        },
        {
            "keywords": ["all", "nachtmagazin", "nacht"],
            "quality": {
                "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/nachtmagazin_https/",
                "webl": "https://www.tagesschau.de/export/video-podcast/webl/nachtmagazin_https/",
                "webm": "https://www.tagesschau.de/export/video-podcast/webm/nachtmagazin_https/",
                "webs": "https://www.tagesschau.de/export/video-podcast/webs/nachtmagazin_https/",
            },
            "default_quality": "webl",
            "input_message_content": True,
        },
        {
            "keywords": ["all", "berichtausberlin", "bericht", "berlin", "bab"],
            "quality": {
                "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/bab_https/",
                "webl": "https://www.tagesschau.de/export/video-podcast/webl/bab_https/",
                "webm": "https://www.tagesschau.de/export/video-podcast/webm/bab_https/",
                "webs": "https://www.tagesschau.de/export/video-podcast/webs/bab_https/",
            },
            "default_quality": "webl",
            "input_message_content": True,
        },
        {
            "keywords": ["all", "tageschau20", "20"],
            "quality": {
                "webxl": "https://www.tagesschau.de/export/video-podcast/webxl/tagesschau-vor-20-jahren_https/",
                "webl": "https://www.tagesschau.de/export/video-podcast/webl/tagesschau-vor-20-jahren_https/",
                "webm": "https://www.tagesschau.de/export/video-podcast/webm/tagesschau-vor-20-jahren_https/",
                "webs": "https://www.tagesschau.de/export/video-podcast/webs/tagesschau-vor-20-jahren_https/",
            },
            "default_quality": "webs",
            "input_message_content": False,
        },
    ]
    return SHOW_CONFIG


if __name__ == "__main__":
    with open("credentials.json") as config:
        key = json.load(config)["key"]

    bot_persistence = PicklePersistence(filename="bot_data", store_bot_data=True)
    updater = Updater(key, persistence=bot_persistence, use_context=True)

    updater.dispatcher.add_handler(InlineQueryHandler(inline_query_handler))
    updater.start_polling()
    updater.idle()
