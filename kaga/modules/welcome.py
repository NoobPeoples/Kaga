import html
import random
import re
import time
from functools import partial

import kaga.modules.sql.welcome_sql as sql
from kaga import (DEV_USERS, LOGGER, OWNER_ID, spamwtc, dispatcher, JOIN_LOGGER)
from kaga.modules.helper_funcs.chat_status import (
    is_user_ban_protected,
    user_admin,
)
from kaga.modules.helper_funcs.alternate import send_message, typing_action
from kaga.modules.helper_funcs.misc import build_keyboard, revert_buttons
from kaga.modules.helper_funcs.msg_types import get_welcome_type
from kaga.modules.helper_funcs.string_handling import (
    escape_invalid_curly_brackets,
    markdown_parser,
)
from kaga.modules.log_channel import loggable
from kaga.modules.sql.global_bans_sql import is_user_gbanned
from telegram import (
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ParseMode,
    Update,
)
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    run_async,
)
from telegram.utils.helpers import escape_markdown, mention_html, mention_markdown

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}
WELCOMEMUTEVIDEO = "https://telegra.ph/file/448b68c62cb25ae933137.gif"

# do not async
def send(update, message, keyboard, backup_message):
    chat = update.effective_chat
    cleanserv = sql.clean_service(chat.id)
    reply = update.message.message_id
    # Clean service welcome
    if cleanserv:
        try:
            dispatcher.bot.delete_message(chat.id, update.message.message_id)
        except BadRequest:
            pass
        reply = False
    try:
        msg = update.effective_message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Button_url_invalid":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message +
                    "\nCatatan: pesan saat ini memiliki url yang tidak valid "
                    "di salah satu tombolnya. Harap perbarui."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Unsupported url protocol":
            msg = update.effective_message.reply_text(
                markdown_parser(backup_message +
                                "\nCatatan: pesan saat ini memiliki tombol yang "
                                "gunakan protokol url yang tidak didukung oleh "
                                "telegram. Harap perbarui."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Wrong url host":
            msg = update.effective_message.reply_text(
                markdown_parser(
                    backup_message +
                    "\nCatatan: pesan saat ini memiliki beberapa url yang buruk. "
                    "Harap perbarui."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Tidak bisa mengurai! mendapat kesalahan host url yang tidak valid")
        elif excp.message == "Tidak punya hak untuk mengirim pesan":
            return
        else:
            msg = update.effective_message.reply_text(
                markdown_parser(backup_message +
                                "\nCatatan: Terjadi kesalahan saat mengirim "
                                "pesan khusus. Harap perbarui."),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.exception()
    return msg


@typing_action
@loggable
def new_member(update, context):
    bot, job_queue = context.bot, context.job_queue
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = sql.get_welc_pref(
        chat.id)
    welc_mutes = sql.welcome_mutes(chat.id)
    human_checks = sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_mem in new_members:

        welcome_log = None
        res = None
        sent = None
        should_mute = True
        welcome_bool = True
        media_wel = False

        if spamwtc != None:
            sw_ban = spamwtc.get_ban(new_mem.id)
            if sw_ban:
                return

        if should_welc:

            reply = update.message.message_id
            cleanserv = sql.clean_service(chat.id)
            # Clean service welcome
            if cleanserv:
                try:
                    dispatcher.bot.delete_message(chat.id,
                                                  update.message.message_id)
                except BadRequest:
                    pass
                reply = False

            # Give the owner a special welcome
            if new_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "My master has come anything can happen 🎉",
                    reply_to_message_id=reply)
                welcome_log = (f"{html.escape(chat.title)}\n"
                               f"#USER_JOINED\n"
                               f"Bot Owner just joined the chat")
                continue

            # Welcome Devs
            elif new_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "My Dev is here don't get killed🔥",
                    reply_to_message_id=reply,
                )
                continue

            # Welcome yourself
            elif new_mem.id == bot.id:
                creator = None
                for x in bot.bot.get_chat_administrators(
                        update.effective_chat.id):
                    if x.status == 'creator':
                        creator = x.user
                        break
                if creator:
                    bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>\n<b>Creator:</b> <code>{}</code>"
                        .format(chat.title, chat.id, creator),
                        parse_mode=ParseMode.HTML)
                else:
                    bot.send_message(
                        JOIN_LOGGER,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>"
                        .format(chat.title, chat.id),
                        parse_mode=ParseMode.HTML)
                update.effective_message.reply_text(
                    "Watashi ga kita!", reply_to_message_id=reply)
                continue

            else:
                buttons = sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (sql.Types.TEXT, sql.Types.BUTTON_TEXT):
                    media_wel = True

                first_name = (
                    new_mem.first_name or "PersonWithNoName"
                )  # edge case of empty name - occurs for some bugs.

                if cust_welcome:
                    if cust_welcome == sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            sql.DEFAULT_WELCOME_MESSAGES).format(
                                first=escape_markdown(first_name))

                    if new_mem.last_name:
                        fullname = escape_markdown(
                            f"{first_name} {new_mem.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    count = chat.get_members_count()
                    mention = mention_markdown(new_mem.id,
                                               escape_markdown(first_name))
                    if new_mem.username:
                        username = "@" + escape_markdown(new_mem.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS)
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_mem.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_mem.id,
                    )

                else:
                    res = random.choice(sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name))
                    keyb = []

                backup_message = random.choice(
                    sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name))
                keyboard = InlineKeyboardMarkup(keyb)

        else:
            welcome_bool = False
            res = None
            keyboard = None
            backup_message = None
            reply = None

        # User exceptions from welcomemutes
        if (is_user_ban_protected(chat, new_mem.id, chat.get_member(new_mem.id))
                or human_checks):
            should_mute = False
        # Join welcome: soft mute
        if new_mem.is_bot:
            should_mute = False

        if user.id == new_mem.id:
            if should_mute:
                if welc_mutes == "soft":
                    bot.restrict_chat_member(
                        chat.id,
                        new_mem.id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_add_web_page_previews=False,
                        ),
                        until_date=(int(time.time() + 24 * 60 * 60)),
                    )
                if welc_mutes == "strong":
                    welcome_bool = False
                    if not media_wel:
                        VERIFIED_USER_WAITLIST.update({
                            new_mem.id: {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                            }
                        })
                    else:
                        VERIFIED_USER_WAITLIST.update({
                            new_mem.id: {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                            }
                        })
                    new_join_mem = f"[{escape_markdown(new_mem.first_name)}](tg://user?id={user.id})"
                    message = msg.reply_text(
                        f"{new_join_mem}, klik tombol di bawah untuk membuktikan bahwa Anda adalah manusia.\nAnda punya 120 detik.",
                        reply_markup=InlineKeyboardMarkup([{
                            InlineKeyboardButton(
                                text="Saya manusia.",
                                callback_data=f"user_join_({new_mem.id})",
                            )
                        }]),
                        parse_mode=ParseMode.MARKDOWN,
                        reply_to_message_id=reply,
                    )
                    bot.restrict_chat_member(
                        chat.id,
                        new_mem.id,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_add_web_page_previews=False,
                        ),
                    )
                    job_queue.run_once(
                        partial(check_not_bot, new_mem, chat.id,
                                message.message_id),
                        480,
                        name="welcomemute",
                    )

        if welcome_bool:
            if media_wel:
                sent = ENUM_FUNC_MAP[welc_type](
                    chat.id,
                    cust_content,
                    caption=res,
                    reply_markup=keyboard,
                    reply_to_message_id=reply,
                    parse_mode="markdown",
                )
            else:
                sent = send(update, res, keyboard, backup_message)
            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

        if welcome_log:
            return welcome_log

        return (f"{html.escape(chat.title)}\n"
                f"#USER_JOINED\n"
                f"<b>User</b>: {mention_html(user.id, user.first_name)}\n"
                f"<b>ID</b>: <code>{user.id}</code>")

    return ""


def check_not_bot(member, chat_id, message_id, context):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop(member.id)
    member_status = member_dict.get("status")
    if not member_status:
        try:
            bot.unban_chat_member(chat_id, member.id)
        except:
            pass

        try:
            bot.edit_message_text(
                "Ya ampun .. Kenapa kau terburu-buru ... Bersikaplah lembutlah.",
                chat_id=chat_id,
                message_id=message_id,
            )
        except:
            pass


@typing_action
def left_member(update, context):
    bot = context.bot
    chat = update.effective_chat
    user = update.effective_user
    should_goodbye, cust_goodbye, goodbye_type = sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return

    if should_goodbye:
        reply = update.message.message_id
        cleanserv = sql.clean_service(chat.id)
        # Clean service welcome
        if cleanserv:
            try:
                dispatcher.bot.delete_message(chat.id,
                                              update.message.message_id)
            except BadRequest:
                pass
            reply = False

        left_mem = update.effective_message.left_chat_member
        if left_mem:

            # Thingy for spamwatched users
            if spamwtc != None:
                sw_ban = spamwtc.get_ban(left_mem.id)
                if sw_ban:
                    return

            # Dont say goodbyes to gbanned users
            if is_user_gbanned(left_mem.id):
                return

            # Ignore bot being kicked
            if left_mem.id == bot.id:
                return

            # Give the owner a special goodbye
            if left_mem.id == OWNER_ID:
                update.effective_message.reply_text(
                    "My master is out ..", reply_to_message_id=reply)
                return

            # Give the devs a special goodbye
            elif left_mem.id in DEV_USERS:
                update.effective_message.reply_text(
                    "Move over the developer I want to pass ...",
                    reply_to_message_id=reply,
                )
                return

            # if media goodbye, use appropriate function for it
            if goodbye_type != sql.Types.TEXT and goodbye_type != sql.Types.BUTTON_TEXT:
                ENUM_FUNC_MAP[goodbye_type](chat.id, cust_goodbye)
                return

            first_name = (left_mem.first_name or "PersonWithNoName"
                         )  # edge case of empty name - occurs for some bugs.
            if cust_goodbye:
                if cust_goodbye == sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(
                        sql.DEFAULT_GOODBYE_MESSAGES).format(
                            first=escape_markdown(first_name))
                if left_mem.last_name:
                    fullname = escape_markdown(
                        f"{first_name} {left_mem.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                count = chat.get_members_count()
                mention = mention_markdown(left_mem.id, first_name)
                if left_mem.username:
                    username = "@" + escape_markdown(left_mem.username)
                else:
                    username = mention

                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS)
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_mem.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_mem.id,
                )
                buttons = sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)

            else:
                res = random.choice(
                    sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name)
                keyb = []

            keyboard = InlineKeyboardMarkup(keyb)

            send(
                update,
                res,
                keyboard,
                random.choice(
                    sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )


@typing_action
@user_admin
def welcome(update, context):
    args = context.args
    chat = update.effective_chat
    # if no args, show current replies.
    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = sql.get_welc_pref(chat.id)
        update.effective_message.reply_text(
            f"Obrolan ini memiliki setelan selamat datang yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat datang (tidak mengisi {{}}) adalah:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type == sql.Types.BUTTON_TEXT or welcome_type == sql.Types.TEXT:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                update.effective_message.reply_text(welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, welcome_m, keyboard, sql.DEFAULT_WELCOME)
        else:
            buttons = sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                ENUM_FUNC_MAP[welcome_type](
                    chat.id, cust_content, caption=welcome_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                ENUM_FUNC_MAP[welcome_type](
                    chat.id,
                    cust_content,
                    caption=welcome_m,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_welc_preference(str(chat.id), True)
            update.effective_message.reply_text(
                "Baik! Saya akan menyapa anggota saat mereka bergabung.")

        elif args[0].lower() in ("off", "no"):
            sql.set_welc_preference(str(chat.id), False)
            update.effective_message.reply_text(
                "Aku akan pergi bermalas-malasan dan tidak menyambut siapa pun.")

        else:
            update.effective_message.reply_text(
                "Saya hanya mengerti 'on/yes' atau 'off/no'!")


@typing_action
@user_admin
def goodbye(update, context):
    args = context.args
    chat = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = sql.get_gdbye_pref(chat.id)
        update.effective_message.reply_text(
            f"Obrolan ini memiliki setelan selamat tinggal yang disetel ke: `{pref}`.\n"
            f"*Pesan selamat tinggal (tidak mengisi {{}}) adalah:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == sql.Types.BUTTON_TEXT:
            buttons = sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                update.effective_message.reply_text(goodbye_m)

            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                send(update, goodbye_m, keyboard, sql.DEFAULT_GOODBYE)

        else:
            if noformat:
                ENUM_FUNC_MAP[goodbye_type](chat.id, goodbye_m)

            else:
                ENUM_FUNC_MAP[goodbye_type](
                    chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN)

    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            sql.set_gdbye_preference(str(chat.id), True)
            update.effective_message.reply_text("Ok!")

        elif args[0].lower() in ("off", "no"):
            sql.set_gdbye_preference(str(chat.id), False)
            update.effective_message.reply_text("Ok!")

        else:
            # idek what you're writing, say yes or no
            update.effective_message.reply_text(
                "Saya hanya mengerti 'on/yes' atau 'off/no'!")


@typing_action
@user_admin
@loggable
def set_welcome(update, context) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan harus membalas dengan apa!")
        return ""

    sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    msg.reply_text("Successfully set custom welcome message!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SET_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Set the welcome message.")


@typing_action
@user_admin
@loggable
def reset_welcome(update, context) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_welcome(chat.id, None, sql.DEFAULT_WELCOME, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil menyetel ulang pesan selamat datang ke default!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESET_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Menyetel ulang pesan selamat datang ke default!")


@typing_action
@user_admin
@loggable
def set_goodbye(update, context) -> str:
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    text, data_type, content, buttons = get_welcome_type(msg)

    if data_type is None:
        msg.reply_text("Anda tidak menentukan harus membalas dengan apa!")
        return ""

    sql.set_custom_gdbye(chat.id, content or text, data_type, buttons)
    msg.reply_text("Berhasil menyetel pesan selamat tinggal kustom!")
    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SET_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Set the goodbye message.")


@typing_action
@user_admin
@loggable
def reset_goodbye(update, context) -> str:
    chat = update.effective_chat
    user = update.effective_user

    sql.set_custom_gdbye(chat.id, sql.DEFAULT_GOODBYE, sql.Types.TEXT)
    update.effective_message.reply_text(
        "Berhasil mengatur ulang pesan selamat tinggal ke default!")

    return (f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESET_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Reset the goodbye message.")


@typing_action
@user_admin
@loggable
def welcomemute(update, context) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            sql.set_welcome_mutes(chat.id, False)
            msg.reply_text("Saya tidak akan lagi menonaktifkan orang saat bergabung!")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>OFF</b>.")
        elif args[0].lower() in ["soft"]:
            sql.set_welcome_mutes(chat.id, "soft")
            msg.reply_text(
                "Saya akan membatasi izin pengguna untuk mengirim media selama 24 jam.")
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>SOFT</b>.")
        elif args[0].lower() in ["strong"]:
            sql.set_welcome_mutes(chat.id, "strong")
            msg.reply_text(
                "Sekarang saya akan menonaktifkan orang ketika mereka bergabung sampai mereka membuktikan bahwa mereka bukan bot.\nMereka memiliki waktu 120 detik sebelum ditendang."
            )
            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>STRONG</b>.")
        else:
            msg.reply_text(
                "Silakan masukkan `off`/`no`/`soft`/`strong`!",
                parse_mode=ParseMode.MARKDOWN,
            )
            return ""
    else:
        curr_setting = sql.welcome_mutes(chat.id)
        reply = (
            f"\n Beri saya pengaturan!\nPilih satu dari: `off`/`no` atau `soft` atau `strong`.\n"
            f"Pengaturan saat ini: `{curr_setting}`")
        msg.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return ""


@typing_action
@user_admin
@loggable
def clean_welcome(update, context) -> str:
    args = context.args
    chat = update.effective_chat
    user = update.effective_user

    if not args:
        clean_pref = sql.get_clean_pref(chat.id)
        if clean_pref:
            update.effective_message.reply_text(
                "Saya harus menghapus pesan selamat datang yang berumur maksimal dua hari.")
        else:
            update.effective_message.reply_text(
                "Saat ini saya tidak menghapus pesan selamat datang yang lama!")
        return ""

    if args[0].lower() in ("on", "yes"):
        sql.set_clean_welcome(str(chat.id), True)
        update.effective_message.reply_text(
            "Saya akan mencoba menghapus pesan selamat datang yang lama!")
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#CLEAN_WELCOME\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled clean welcomes to <code>ON</code>.")
    elif args[0].lower() in ("off", "no"):
        sql.set_clean_welcome(str(chat.id), False)
        update.effective_message.reply_text(
            "Saya tidak akan menghapus pesan selamat datang yang lama.")
        return (f"<b>{html.escape(chat.title)}:</b>\n"
                f"#CLEAN_WELCOME\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled clean welcomes to <code>OFF</code>.")
    else:
        update.effective_message.reply_text(
            "Saya hanya mengerti 'on/yes' atau 'off/no'.")
        return ""


@typing_action
@user_admin
def cleanservice(update, context) -> str:
    args = context.args
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE:
        if len(args) >= 1:
            var = args[0]
            if var in ("no", "off"):
                sql.set_clean_service(chat.id, False)
                update.effective_message.reply_text(
                    "Layanan pembersihan selamat datang : off")
            elif var in ("yes", "on"):
                sql.set_clean_service(chat.id, True)
                update.effective_message.reply_text(
                    "Layanan pembersihan selamat datang : on")
            else:
                update.effective_message.reply_text(
                    "Opsi tidak valid", parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text(
                "Penggunaan on/yes atau off/no", parse_mode=ParseMode.MARKDOWN)
    else:
        curr = sql.clean_service(chat.id)
        if curr:
            update.effective_message.reply_text(
                "Layanan pembersihan selamat datang : on", parse_mode=ParseMode.MARKDOWN)
        else:
            update.effective_message.reply_text(
                "Layanan pembersihan selamat datang : off", parse_mode=ParseMode.MARKDOWN)


@typing_action
def user_button(update, context):
    chat = update.effective_chat
    user = update.effective_user
    query = update.callback_query
    bot = context.bot
    match = re.match(r"user_join_\((.+?)\)", query.data)
    message = update.effective_message
    join_user = int(match.group(1))

    if join_user == user.id:
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id)
        member_dict["status"] = True
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        query.answer(text="Horey! Anda seorang manusia, disuarakan!")
        bot.restrict_chat_member(
            chat.id,
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        bot.deleteMessage(chat.id, message.message_id)
        if member_dict["should_welc"]:
            if member_dict["media_wel"]:
                sent = ENUM_FUNC_MAP[member_dict["welc_type"]](
                    member_dict["chat_id"],
                    member_dict["cust_content"],
                    caption=member_dict["res"],
                    reply_markup=member_dict["keyboard"],
                    parse_mode="markdown",
                )
            else:
                sent = send(
                    member_dict["update"],
                    member_dict["res"],
                    member_dict["keyboard"],
                    member_dict["backup_message"],
                )

            prev_welc = sql.get_clean_pref(chat.id)
            if prev_welc:
                try:
                    bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    sql.set_clean_welcome(chat.id, sent.message_id)

    else:
        query.answer(text="Anda tidak diizinkan melakukan ini!")


WELC_HELP_TXT = (
    "Pesan selamat datang/selamat tinggal grup Anda dapat dipersonalisasi dengan berbagai cara. Jika Anda menginginkan pesan"
    " untuk dibuat satu per satu, seperti pesan selamat datang default, Anda dapat menggunakan variabel *ini*:\n"
    " • `{first}`*:* ini mewakili nama *depan* pengguna\n"
    " • `{last}`*:* ini mewakili nama *belakang* pengguna. Default-nya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " • `{fullname}`*:* ini mewakili nama *lengkap* pengguna. Default-nya adalah *nama depan* jika pengguna tidak memiliki "
    "nama belakang.\n"
    " • `{username}`*:* ini mewakili *username* pengguna. Secara default, *sebutan* pengguna "
    "nama depan jika tidak memiliki nama pengguna.\n"
    " • `{mention}`*:* ini hanya *menyebutkan* pengguna - memberi tag mereka dengan nama depan mereka.\n"
    " • `{id}`*:* ini mewakili *id* pengguna\n"
    " • `{count}`*:* ini mewakili *nomor anggota* pengguna.\n"
    " • `{chatname}`*:* ini mewakili *nama obrolan saat ini*.\n"
    "\nini mewakili * nama obrolan saat ini *.\n"
    "Pesan selamat datang juga mendukung penurunan harga, sehingga Anda dapat membuat elemen apa pun seperti bold/italic/code/links. "
    "Tombol juga didukung, sehingga Anda dapat membuat sambutan Anda terlihat luar biasa dengan beberapa tombol intro yang "
    "bagus.\n"
    f"Untuk membuat tombol yang menautkan ke aturan Anda, gunakan ini: `[Rules](buttonurl://t.me/{dispatcher.bot.username}?start=group_id)`. "
    "Cukup ganti `group_id` dengan id grup Anda, yang dapat diperoleh melalui /id, dan Anda siap pergi melakukannya. "
    "Perhatikan bahwa id grup biasanya diawali dengan tanda `-`; ini diperlukan, jadi tolong jangan "
    "disingkirkan.\n"
    "Anda bahkan dapat mengatur gambar/gif/video/pesan suara sebagai pesan selamat datang oleh "
    "membalas media yang diinginkan, dan menelepon `/setwelcome`.")

WELC_MUTE_HELP_TXT = (
    "Anda bisa mendapatkan bot untuk menonaktifkan orang baru yang bergabung dengan grup Anda dan karenanya mencegah robot spam membanjiri grup Anda. "
    "Opsi berikut dimungkinkan:\n"
    "• `/welcomemute soft`*:* membatasi anggota baru mengirim media selama 24 jam.\n"
    "• `/welcomemute strong`*:*membungkam anggota baru sampai mereka mengetuk tombol sehingga memverifikasi bahwa mereka manusia.\n"
    "• `/welcomemute off`*:* mematikan welcomemute.\n"
    "*Catatan:* Mode kuat menendang pengguna dari obrolan jika mereka tidak memverifikasi dalam 120 detik. Mereka selalu bisa bergabung kembali"
)


@typing_action
@user_admin
def welcome_help(update, context):
    update.effective_message.reply_text(
        WELC_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


@typing_action
@user_admin
def welcome_mute_help(update, context):
    update.effective_message.reply_text(
        WELC_MUTE_HELP_TXT, parse_mode=ParseMode.MARKDOWN)


# TODO: get welcome data from group butler snap
# def __import_data__(chat_id, data):
#     welcome = data.get('info', {}).get('rules')
#     welcome = welcome.replace('$username', '{username}')
#     welcome = welcome.replace('$name', '{fullname}')
#     welcome = welcome.replace('$id', '{id}')
#     welcome = welcome.replace('$title', '{chatname}')
#     welcome = welcome.replace('$surname', '{lastname}')
#     welcome = welcome.replace('$rules', '{rules}')
#     sql.set_custom_welcome(chat_id, welcome, sql.Types.TEXT)


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    welcome_pref, _, _ = sql.get_welc_pref(chat_id)
    goodbye_pref, _, _ = sql.get_gdbye_pref(chat_id)
    return ("Obrolan ini memiliki preferensi selamat datang yang disetel ke `{}`.\n"
            "Ini preferensi selamat tinggal`{}`.".format(welcome_pref,
                                                      goodbye_pref))


__help__ = """
*Khsus Admin:*
 × /welcome <on/off>*:* aktifkan/nonaktifkan pesan selamat datang.
 × /welcome*:* menunjukkan pengaturan selamat datang saat ini.
 × /welcome noformat*:* menunjukkan pengaturan selamat datang saat ini, tanpa pemformatan - berguna untuk mendaur ulang pesan selamat datang Anda!
 × /goodbye*:* penggunaan dan argumen yang sama seperti `/welcome`.
 × /setwelcome <sometext>*:* setel pesan selamat datang khusus. Jika digunakan membalas media, gunakan media itu.
 × /setgoodbye <sometext>*:* setel pesan selamat jalan khusus. Jika digunakan membalas media, gunakan media itu.
 × /resetwelcome*:* setel ulang ke pesan selamat datang default.
 × /resetgoodbye*:* setel ulang ke pesan selamat jalan default.
 × /cleanwelcome <on/off>*:* Pada anggota baru, coba hapus pesan selamat datang sebelumnya untuk menghindari spamming pada obrolan.
 × /welcomemutehelp*:* memberikan informasi tentang pembungkaman selamat datang.
 × /cleanservice <on/off*:* menghapus pesan layanan selamat datang / tinggalkan telegram.
 *Contoh:*
pengguna bergabung dengan obrolan, pengguna meninggalkan obrolan.

*Welcome markdown:*
 • /welcomehelp*:* lihat lebih banyak informasi pemformatan untuk pesan selamat datang/selamat tinggal khusus.
"""

NEW_MEM_HANDLER = MessageHandler(Filters.status_update.new_chat_members,
                                 new_member, run_async=True)
LEFT_MEM_HANDLER = MessageHandler(Filters.status_update.left_chat_member,
                                  left_member, run_async=True)
WELC_PREF_HANDLER = CommandHandler("welcome", welcome, filters=Filters.chat_type.groups, run_async=True)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, filters=Filters.chat_type.groups, run_async=True)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=Filters.chat_type.groups, run_async=True)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=Filters.chat_type.groups, run_async=True)
RESET_WELCOME = CommandHandler(
    "resetwelcome", reset_welcome, filters=Filters.chat_type.groups, run_async=True)
RESET_GOODBYE = CommandHandler(
    "resetgoodbye", reset_goodbye, filters=Filters.chat_type.groups, run_async=True)
WELCOMEMUTE_HANDLER = CommandHandler(
    "welcomemute", welcomemute, filters=Filters.chat_type.groups, run_async=True)
CLEAN_SERVICE_HANDLER = CommandHandler(
    "cleanservice", cleanservice, filters=Filters.chat_type.groups, run_async=True)
CLEAN_WELCOME = CommandHandler(
    "cleanwelcome", clean_welcome, filters=Filters.chat_type.groups, run_async=True)
WELCOME_HELP = CommandHandler("welcomehelp", welcome_help, run_async=True)
WELCOME_MUTE_HELP = CommandHandler("welcomemutehelp", welcome_mute_help, run_async=True)
BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_", run_async=True)

dispatcher.add_handler(NEW_MEM_HANDLER)
dispatcher.add_handler(LEFT_MEM_HANDLER)
dispatcher.add_handler(WELC_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(WELCOME_HELP)
dispatcher.add_handler(WELCOMEMUTE_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(WELCOME_MUTE_HELP)

__mod_name__ = "Greetings"
__command_list__ = []
__handlers__ = [
    NEW_MEM_HANDLER,
    LEFT_MEM_HANDLER,
    WELC_PREF_HANDLER,
    GOODBYE_PREF_HANDLER,
    SET_WELCOME,
    SET_GOODBYE,
    RESET_WELCOME,
    RESET_GOODBYE,
    CLEAN_WELCOME,
    WELCOME_HELP,
    WELCOMEMUTE_HANDLER,
    CLEAN_SERVICE_HANDLER,
    BUTTON_VERIFY_HANDLER,
    WELCOME_MUTE_HELP,
]
