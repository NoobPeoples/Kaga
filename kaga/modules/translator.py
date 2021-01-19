import json
import os

import requests
from emoji import UNICODE_EMOJI
from google_trans_new import google_translator, LANGUAGES
from gtts import gTTS
from telegram import ChatAction
from telegram.utils.helpers import escape_markdown

from kaga import dispatcher
from kaga.modules.disable import DisableAbleCommandHandler
from kaga.modules.helper_funcs.alternate import send_action, typing_action


@typing_action
def gtrans(update, context):
    msg = update.effective_message
    args = context.args
    lang = " ".join(args)
    if not lang:
        lang = "id"
    try:
        translate_text = (
            msg.reply_to_message.text or msg.reply_to_message.caption
        )
    except AttributeError:
        return msg.reply_text("Beri aku teks untuk diterjemahkan!")

    ignore_text = UNICODE_EMOJI.keys()
    for emoji in ignore_text:
        if emoji in translate_text:
            translate_text = translate_text.replace(emoji, "")

    translator = google_translator()
    try:
        translated = translator.translate(translate_text, lang_tgt=lang)
        source_lan = translator.detect(translate_text)[1].title()
        des_lan = LANGUAGES.get(lang).title()
        msg.reply_text(
            "Diterjemahkan dari {} ke {}.\n {}".format(
                source_lan, des_lan, translated
            )
        )
    except BaseException:
        msg.reply_text("Kesalahan! kode bahasa tidak valid.")


@send_action(ChatAction.RECORD_AUDIO)
def gtts(update, context):
    msg = update.effective_message
    reply = " ".join(context.args)
    if not reply:
        if msg.reply_to_message:
            reply = msg.reply_to_message.text
        else:
            return msg.reply_text(
                "Balas beberapa pesan atau masukkan beberapa teks untuk mengubahnya menjadi format audio!"
            )
        for x in "\n":
            reply = reply.replace(x, "")
    try:
        tts = gTTS(reply)
        tts.save("Violetrobot.mp3")
        with open("Violetrobot.mp3", "rb") as speech:
            msg.reply_audio(speech)
    finally:
        if os.path.isfile("Violetrobot.mp3"):
            os.remove("Violetrobot.mp3")


# Open API key
API_KEY = "6ae0c3a0-afdc-4532-a810-82ded0054236"
URL = "http://services.gingersoftware.com/Ginger/correct/json/GingerTheText"


@typing_action
def spellcheck(update, context):
    if update.effective_message.reply_to_message:
        msg = update.effective_message.reply_to_message

        params = dict(
            lang="US", clientVersion="2.0", apiKey=API_KEY, text=msg.text
        )

        res = requests.get(URL, params=params)
        changes = json.loads(res.text).get("LightGingerTheTextResult")
        curr_string = ""
        prev_end = 0

        for change in changes:
            start = change.get("From")
            end = change.get("To") + 1
            suggestions = change.get("Suggestions")
            if suggestions:
                # should look at this list more
                sugg_str = suggestions[0].get("Text")
                curr_string += msg.text[prev_end:start] + sugg_str
                prev_end = end

        curr_string += msg.text[prev_end:]
        update.effective_message.reply_text(curr_string)
    else:
        update.effective_message.reply_text(
            "Balas beberapa pesan untuk mendapatkan teks koreksi tata bahasa!"
        )


__help__ = """
× /tr atau /tl: - Untuk menerjemahkan ke bahasa Anda, secara default bahasa diatur ke bahasa Inggris, gunakan `/tr <lang code>` untuk beberapa bahasa lain!
× /spell: - Sebagai balasan untuk mendapatkan koreksi tata bahasa teks pesan nonsens.
× /tts: - Untuk beberapa pesan untuk mengubahnya menjadi format audio!
"""
__mod_name__ = "Translate"

dispatcher.add_handler(
    DisableAbleCommandHandler(
        ["tr", "tl"], gtrans, pass_args=True, run_async=True
    )
)
dispatcher.add_handler(
    DisableAbleCommandHandler("tts", gtts, pass_args=True, run_async=True)
)
dispatcher.add_handler(
    DisableAbleCommandHandler("spell", spellcheck, run_async=True)
)
