import importlib
import traceback
import html
import json
import re
import requests
from typing import Optional

from telegram import Message, Chat, User
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import Unauthorized
from telegram.ext import (
    CommandHandler,
    Filters,
    MessageHandler,
    CallbackQueryHandler,
)
from telegram.ext.dispatcher import DispatcherHandlerStop
from telegram.utils.helpers import escape_markdown
from sqlalchemy.exc import SQLAlchemyError, DBAPIError

from kaga import (
    dispatcher,
    DEV_USERS,
    SUDO_USERS,
    SUPPORT_USERS,
    updater,
    TOKEN,
    MESSAGE_DUMP,
    WEBHOOK,
    CERT_PATH,
    PORT,
    URL,
    LOGGER,
    BLACKLIST_CHATS,
    WHITELIST_CHATS,
)

# needed to dynamically load modules
# NOTE: Module order is not guaranteed, specify that in the config file!
from kaga.modules import ALL_MODULES
from kaga.modules.helper_funcs.chat_status import is_user_admin
from kaga.modules.helper_funcs.filters import CustomFilters
from kaga.modules.helper_funcs.misc import paginate_modules
from kaga.modules.helper_funcs.alternate import typing_action


PM_START_TEXT = f"""
Hai, perkenalkan nama saya adalah *{dispatcher.bot.first_name}*.
Saya adalah bot manajemen grup bertema Anime dengan banyak Fitur Khusus.
Anda dapat menemukan daftar perintah yang tersedia dengan /help.

Bergabunglah di [Group](https://t.me/ZeroBotSupport) Jika Anda ingin Melaporkan Masalah 🙂

Saya di sini untuk membuat pengelolaan grup Anda menyenangkan dan mudah!
Saya memiliki banyak fitur praktis ☺️ seperti:

• Anime
• Pengendalian flood.
• Sistem penyimpanan Note.
• Sistem Warning.

*Dikelolah oleh ❤️:* [Ihsan #](https://t.me/RxyMX)

Ingin menambahkan saya ke grup Anda? Cukup klik tombol di bawah!
"""

buttons = [
    [
        InlineKeyboardButton(
            text="Tambahkan Saya ke Grup 👥", url="t.me/VioletsRobot?startgroup=true"
        ),
    ]
]


buttons += [
    [
        InlineKeyboardButton(
            text="Help & Commands ❔",
            url=f"t.me/{dispatcher.bot.username}?start=help",
        ),
        InlineKeyboardButton(
            text="Gban Logs 🚫", url="https://t.me/joinchat/VN_35KFkyhNcVqdj"
        ),
        
    ]
]

buttons += [
    [
        InlineKeyboardButton(
            text="Support 🎗️", url="https://t.me/ZeroBotSupport"
        ),
        InlineKeyboardButton(
            text="Channel 📢", url="https://t.me/HayakaRyuUpdates"
        ),
    ]
]



HELP_STRINGS = f"""
Halo! Nama saya adalah *{dispatcher.bot.first_name}*.
Saya bot manajemen grup bertema Anime dengan beberapa tambahan yang menyenangkan! Lihatlah yang berikut ini untuk mendapatkan gambaran tentang beberapa \
hal-hal yang dapat saya bantu.

*Perintah utama* yang tersedia:
 × /start: Mulai saya, dapat digunakan untuk memeriksa saya masih hidup atau tidak...
 × /help: PM Anda ke pesan ini.
 × /help <nama modul>: PM Anda info tentang modul itu.
 × /settings: di PM: akan mengirimkan pengaturan Anda untuk semua modul yang didukung.
   - dalam grup: akan mengarahkan Anda ke pm, dengan semua pengaturan obrolan itu.
 \nKlik tombol di bawah ini untuk mendapatkan dokumentasi tentang modul tertentu!"""


STAFF_HELP_STRINGS = """Halo pengguna staf. Senang bertemu Anda :)
Ini semua perintah staf. Pengguna di atas memiliki akses perintah untuk semua perintah di bawah ini.

*OWNER*
× /broadcast: Kirim pesan siaran ke semua obrolan yang saya ikuti saat ini.
× /staffids: Dapatkan semua staf yang Anda miliki.
× /ip: Mengirimkan alamat IP bot ke ssh jika perlu (khusus PM).

*DEV*
× /gitpull: Tarik pembaruan terbaru.
× /reboot: Mulai ulang bot.
× /dbcleanup: Bersihkan database saya yang tidak valid.
× /leavemutedchats: Tinggalkan semua obrolan di mana saya tidak bisa mengirim pesan.
× /leave <chatid>: Katakan padaku untuk meninggalkan grup tertentu. (alias /leavechat /leavegroup).
× /stats: Daftar semua blacklist, filter, federation, gbans, dll dari semua grup.
× /getlink <chatid>: Dapatkan tautan undangan obrolan.
× /sysinfo: Dapatkan info sistem saya.

*SUDO*
× /snipe <chatid> <string>: Beri tahu saya untuk mengirim pesan ke obrolan yang diberikan.
× /echo <string>: Seperti snipe tetapi pada obrolan saat ini.
× /chatlist: Dapatkan daftar obrolan yang saat ini saya ikuti.
× /ping: Mulailah tes ping.
× /speedtest: Mulai uji kecepatan dari server saya.

*SUPPORT*
× /gban <userid>: larangan global pengguna.
× /ungban <userid>: hapus pengguna yang saat ini dilarang.
× /gbanlist: Dapatkan daftar pengguna yang diblokir saat ini."""


IMPORTED = {}
MIGRATEABLE = []
HELPABLE = {}
STATS = []
USER_INFO = []
DATA_IMPORT = []
DATA_EXPORT = []

CHAT_SETTINGS = {}
USER_SETTINGS = {}

GDPR = []

for module_name in ALL_MODULES:
    imported_module = importlib.import_module(
        "kaga.modules." + module_name
    )
    importlib.reload(imported_module)
    if not hasattr(imported_module, "__mod_name__"):
        imported_module.__mod_name__ = imported_module.__name__

    if not imported_module.__mod_name__.lower() in IMPORTED:
        IMPORTED[imported_module.__mod_name__.lower()] = imported_module
    else:
        raise Exception(
            "Can't have two modules with the same name! Please change one"
        )

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE[imported_module.__mod_name__.lower()] = imported_module

    # Chats to migrate on chat_migrated events
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE.append(imported_module)

    if hasattr(imported_module, "__stats__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__gdpr__"):
        GDPR.append(imported_module)

    if hasattr(imported_module, "__user_info__"):
        USER_INFO.append(imported_module)

    if hasattr(imported_module, "__import_data__"):
        DATA_IMPORT.append(imported_module)

    if hasattr(imported_module, "__export_data__"):
        DATA_EXPORT.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__mod_name__.lower()] = imported_module

    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__mod_name__.lower()] = imported_module


# do not async
def send_help(chat_id, text, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    dispatcher.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
    )


def test(update, context):
    try:
        print(update)
    except BaseException:
        pass
    update.effective_message.reply_text(
        "Hola tester! _I_ *have* `markdown`", parse_mode=ParseMode.MARKDOWN
    )
    update.effective_message.reply_text("This person edited a message")
    print(update.effective_message)


@typing_action
def start(update, context):
    if update.effective_chat.type == "private":
        args = context.args
        if len(args) >= 1:
            if args[0].lower() == "help":
                user = update.effective_user
                keyb = paginate_modules(0, HELPABLE, "help")

                if (
                    user.id in DEV_USERS
                    or user.id in SUDO_USERS
                    or user.id in SUPPORT_USERS
                ):
                    keyb += [
                        [
                            InlineKeyboardButton(
                                text="Staff", callback_data="help_staff"
                            )
                        ]
                    ]

                send_help(
                    update.effective_chat.id,
                    HELP_STRINGS,
                    InlineKeyboardMarkup(keyb),
                )

            elif args[0].lower().startswith("stngs_"):
                match = re.match("stngs_(.*)", args[0].lower())
                chat = dispatcher.bot.getChat(match.group(1))

                if is_user_admin(chat, update.effective_user.id):
                    send_settings(
                        match.group(1), update.effective_user.id, False
                    )
                else:
                    send_settings(
                        match.group(1), update.effective_user.id, True
                    )

            elif args[0][1:].isdigit() and "rules" in IMPORTED:
                IMPORTED["rules"].send_rules(update, args[0], from_pm=True)

        else:
            update.effective_message.reply_photo(
                "https://telegra.ph/file/b100befa6ebae55a4fd75.mp4",
                PM_START_TEXT,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode=ParseMode.MARKDOWN,
                timeout=60,
            )
    else:
        update.effective_message.reply_text(
            "Mengirimi Anda salam hangat & berharap hari Anda menyenangkan!"
        )


def error_handler(update, context):
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    LOGGER.error(
        msg="Exception while handling an update:", exc_info=context.error
    )
    if isinstance(context.error, SQLAlchemyError) or isinstance(
        context.error, DBAPIError
    ):
        return
    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    else:
        tb_list = traceback.format_exception(
            None, context.error, context.error.__traceback__
        )
        tb_string = "".join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        message = (
            f"An exception was raised while handling an update\n"
            f"update = {(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}"
            "\n\n"
            f"context.chat_data = {(str(context.chat_data))}\n\n"
            f"context.user_data = {(str(context.user_data))}\n\n"
            f"{(tb_string)}"
        )

        key = (
            requests.post(
                "https://nekobin.com/api/documents", json={"content": message}
            )
            .json()
            .get("result")
            .get("key")
        )
        markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Nekobin Url", url=f"https://nekobin.com/{key}"
                    ),
                    InlineKeyboardButton(
                        "Nekobin Raw", url=f"https://nekobin.com/raw/{key}"
                    ),
                ]
            ]
        )

    # Finally, send the message
    context.bot.send_message(
        chat_id=MESSAGE_DUMP,
        text="kesalahan telah ditemukan di sini !!!",
        reply_markup=markup,
    )


def help_button(update, context):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    staff_match = re.match(r"help_staff", query.data)
    back_match = re.match(r"help_back", query.data)
    try:
        if mod_match:
            module = mod_match.group(1)
            text = (
                "Berikut adalah bantuan untuk modul *{}*:\n".format(
                    HELPABLE[module].__mod_name__
                )
                + HELPABLE[module].__help__
            )
            query.message.edit_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="⬅️ Kembali", callback_data="help_back"
                            )
                        ]
                    ]
                ),
            )

        elif staff_match:
            query.message.edit_text(
                text=STAFF_HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="⬅️ Kembali", callback_data="help_back"
                            )
                        ]
                    ]
                ),
            )

        elif back_match:
            keyb = paginate_modules(0, HELPABLE, "help")
            # Add aditional button if staff user detected
            if (
                user.id in DEV_USERS
                or user.id in SUDO_USERS
                or user.id in SUPPORT_USERS
            ):
                keyb += [
                    [
                        InlineKeyboardButton(
                            text="Staff", callback_data="help_staff"
                        )
                    ]
                ]

            query.message.edit_text(
                text=HELP_STRINGS,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyb),
            )

        # ensure no spinny white circle
        context.bot.answer_callback_query(query.id)
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception("Exception in help buttons. %s", str(query.data))


@typing_action
def staff_help(update, context):
    chat = update.effective_chat
    user = update.effective_user

    if chat.type != chat.PRIVATE:
        update.effective_message.reply_text(
            "Hubungi saya di PM untuk mendapatkan daftar perintah staf"
        )
        return

    if (
        user.id in DEV_USERS
        or user.id in SUDO_USERS
        or user.id in SUPPORT_USERS
    ):
        update.effective_message.reply_text(
            text=STAFF_HELP_STRINGS,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Modul help", callback_data="help_back"
                        )
                    ]
                ]
            ),
        )
    else:
        update.effective_message.reply_text("Anda tidak dapat mengakses perintah ini")


@typing_action
def get_help(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    # ONLY send help in PM
    if chat.type != chat.PRIVATE:

        update.effective_message.reply_text(
            "Hubungi saya di PM untuk mendapatkan daftar perintah yang ada.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Bantuan",
                            url="t.me/{}?start=help".format(
                                context.bot.username
                            ),
                        )
                    ]
                ]
            ),
        )
        return

    elif len(args) >= 2 and any(args[1].lower() == x for x in HELPABLE):
        module = args[1].lower()
        text = (
            "Berikut adalah bantuan yang tersedia untuk modul *{}*:\n".format(
                HELPABLE[module].__mod_name__
            )
            + HELPABLE[module].__help__
        )
        send_help(
            chat.id,
            text,
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Kembali", callback_data="help_back"
                        )
                    ]
                ]
            ),
        )

    else:
        keyb = paginate_modules(0, HELPABLE, "help")
        # Add aditional button if staff user detected
        if (
            user.id in DEV_USERS
            or user.id in SUDO_USERS
            or user.id in SUPPORT_USERS
        ):
            keyb += [
                [
                    InlineKeyboardButton(
                        text="Staff", callback_data="help_staff"
                    )
                ]
            ]

        send_help(chat.id, HELP_STRINGS, InlineKeyboardMarkup(keyb))


def send_settings(chat_id, user_id, user=False):
    if user:
        if USER_SETTINGS:
            settings = "\n\n".join(
                "*{}*:\n{}".format(
                    mod.__mod_name__, mod.__user_settings__(user_id)
                )
                for mod in USER_SETTINGS.values()
            )
            dispatcher.bot.send_message(
                user_id,
                "Ini adalah pengaturan Anda saat ini:" + "\n\n" + settings,
                parse_mode=ParseMode.MARKDOWN,
            )

        else:
            dispatcher.bot.send_message(
                user_id,
                "Sepertinya tidak ada pengaturan khusus pengguna yang tersedia :'(",
                parse_mode=ParseMode.MARKDOWN,
            )

    else:
        if CHAT_SETTINGS:
            chat_name = dispatcher.bot.getChat(chat_id).title
            dispatcher.bot.send_message(
                user_id,
                text="Modul mana yang ingin Anda periksa setelan {}?".format(
                    chat_name
                ),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )
        else:
            dispatcher.bot.send_message(
                user_id,
                "Sepertinya tidak ada pengaturan obrolan yang tersedia :'(\nKirim ini di "
                "dalam obrolan grup tempat Anda menjadi admin untuk menemukan pengaturannya saat ini!",
                parse_mode=ParseMode.MARKDOWN,
            )


def settings_button(update, context):
    query = update.callback_query
    user = update.effective_user
    mod_match = re.match(r"stngs_module\((.+?),(.+?)\)", query.data)
    prev_match = re.match(r"stngs_prev\((.+?),(.+?)\)", query.data)
    next_match = re.match(r"stngs_next\((.+?),(.+?)\)", query.data)
    back_match = re.match(r"stngs_back\((.+?)\)", query.data)
    try:
        if mod_match:
            chat_id = mod_match.group(1)
            module = mod_match.group(2)
            chat = context.bot.get_chat(chat_id)
            text = "*{}* memiliki pengaturan berikut untuk modul *{}*:\n\n".format(
                escape_markdown(chat.title), CHAT_SETTINGS[module].__mod_name__
            ) + CHAT_SETTINGS[
                module
            ].__chat_settings__(
                chat_id, user.id
            )
            query.message.reply_text(
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Kembali",
                                callback_data="stngs_back({})".format(chat_id),
                            )
                        ]
                    ]
                ),
            )

        elif prev_match:
            chat_id = prev_match.group(1)
            curr_page = int(prev_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                "Halo yang disana! Ada beberapa setelan untuk {} - lanjutkan dan pilih apa "
                "bikin Anda tertarik.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        curr_page - 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif next_match:
            chat_id = next_match.group(1)
            next_page = int(next_match.group(2))
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                "Halo yang disana! Ada beberapa setelan untuk {} - lanjutkan dan pilih apa "
                "bikin Anda tertarik.".format(chat.title),
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(
                        next_page + 1, CHAT_SETTINGS, "stngs", chat=chat_id
                    )
                ),
            )

        elif back_match:
            chat_id = back_match.group(1)
            chat = context.bot.get_chat(chat_id)
            query.message.reply_text(
                text="Halo yang disana! Ada beberapa setelan untuk {} - lanjutkan dan pilih apa "
                "bikin Anda tertarik.".format(escape_markdown(chat.title)),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(
                    paginate_modules(0, CHAT_SETTINGS, "stngs", chat=chat_id)
                ),
            )

        # ensure no spinny white circle
        query.message.delete()
        context.bot.answer_callback_query(query.id)
    except Exception as excp:
        if excp.message == "Message is not modified":
            pass
        elif excp.message == "Query_id_invalid":
            pass
        elif excp.message == "Message can't be deleted":
            pass
        else:
            query.message.edit_text(excp.message)
            LOGGER.exception(
                "Exception in settings buttons. %s", str(query.data)
            )


@typing_action
def get_settings(update, context):
    chat = update.effective_chat  # type: Optional[Chat]
    user = update.effective_user  # type: Optional[User]
    msg = update.effective_message  # type: Optional[Message]
    msg.text.split(None, 1)

    # ONLY send settings in PM
    if chat.type != chat.PRIVATE:
        if is_user_admin(chat, user.id):
            text = "Klik di sini untuk mendapatkan pengaturan obrolan ini, serta milik Anda."
            msg.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="Pengaturan",
                                url="t.me/{}?start=stngs_{}".format(
                                    context.bot.username, chat.id
                                ),
                            )
                        ]
                    ]
                ),
            )
        else:
            text = "Klik di sini untuk memeriksa pengaturan Anda."

    else:
        send_settings(chat.id, user.id, True)


def migrate_chats(update, context):
    msg = update.effective_message  # type: Optional[Message]
    if msg.migrate_to_chat_id:
        old_chat = update.effective_chat.id
        new_chat = msg.migrate_to_chat_id
    elif msg.migrate_from_chat_id:
        old_chat = msg.migrate_from_chat_id
        new_chat = update.effective_chat.id
    else:
        return

    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE:
        mod.__migrate__(old_chat, new_chat)

    LOGGER.info("Successfully migrated!")
    raise DispatcherHandlerStop


def is_chat_allowed(update, context):
    if len(WHITELIST_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id not in WHITELIST_CHATS:
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Grup ini Masuk Daftar Hitam! Out ah 😅...",
                )
                context.bot.leave_chat(chat_id)
            except Unauthorized:
                pass
            finally:
                raise DispatcherHandlerStop
    if len(BLACKLIST_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id in BLACKLIST_CHATS:
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Grup ini Masuk Daftar Hitam! Out ah 😅...",
                )
                context.bot.leave_chat(chat_id)
            except Unauthorized:
                pass
            finally:
                raise DispatcherHandlerStop
    if len(WHITELIST_CHATS) != 0 and len(BLACKLIST_CHATS) != 0:
        chat_id = update.effective_message.chat_id
        if chat_id in BLACKLIST_CHATS:
            try:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="Grup ini Masuk Daftar Hitam! Out ah 😅..."
                )
                context.bot.leave_chat(chat_id)
            except Unauthorized:
                pass
            finally:
                raise DispatcherHandlerStop


def main():
    # test_handler = CommandHandler("test", test)
    start_handler = CommandHandler(
        "start", start, pass_args=True, run_async=True
    )

    help_handler = CommandHandler("help", get_help)
    help_callback_handler = CallbackQueryHandler(
        help_button, pattern=r"help_", run_async=True
    )
    help_staff_handler = CommandHandler(
        "staffhelp",
        staff_help,
        filters=CustomFilters.support_filter,
        run_async=True,
    )

    settings_handler = CommandHandler("settings", get_settings, run_async=True)
    settings_callback_handler = CallbackQueryHandler(
        settings_button, pattern=r"stngs_", run_async=True
    )

    migrate_handler = MessageHandler(
        Filters.status_update.migrate, migrate_chats
    )
    is_chat_allowed_handler = MessageHandler(Filters.chat_type.groups, is_chat_allowed)

    # dispatcher.add_handler(test_handler)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(settings_handler)
    dispatcher.add_handler(help_callback_handler)
    dispatcher.add_handler(help_staff_handler)
    dispatcher.add_handler(settings_callback_handler)
    dispatcher.add_handler(migrate_handler)
    dispatcher.add_handler(is_chat_allowed_handler)
    dispatcher.add_error_handler(error_handler)

    if WEBHOOK:
        LOGGER.info("Using webhooks.")
        updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=TOKEN)

        if CERT_PATH:
            updater.bot.set_webhook(
                url=URL + TOKEN, certificate=open(CERT_PATH, "rb")
            )
        else:
            updater.bot.set_webhook(url=URL + TOKEN)

    else:
        LOGGER.info("Using long polling.")
        updater.start_polling(timeout=15, read_latency=5, clean=True)
        if MESSAGE_DUMP:
            updater.bot.send_message(
                chat_id=MESSAGE_DUMP, text="Sistem telah aktif..."
            )

    updater.idle()


if __name__ == "__main__":
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()
