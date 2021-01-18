import html
from io import BytesIO

from requests import get
from telegram import ChatAction, ParseMode
from telegram.error import BadRequest, TelegramError, Unauthorized
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.utils.helpers import mention_html

import kaga.modules.no_sql.gban_db as gban_db
from kaga import STRICT_GBAN  # LOGGER,
from kaga import (
    DEV_USERS,
    GBAN_LOGS,
    OWNER_ID,
    SUDO_USERS,
    SUPPORT_USERS,
    dispatcher,
    spamwtc,
)
from kaga.modules.helper_funcs.alternate import (
    send_action,
    send_message,
    typing_action,
)
from kaga.modules.helper_funcs.chat_status import is_user_admin, user_admin
from kaga.modules.helper_funcs.extraction import (
    extract_user,
    extract_user_and_text,
)
from kaga.modules.helper_funcs.filters import CustomFilters
from kaga.modules.no_sql.users_db import get_all_chats

GBAN_ENFORCE_GROUP = 6

GBAN_ERRORS = {
    "Bot tidak dapat menambahkan anggota obrolan baru",
    "Channel_private",
    "Obrolan tidak ditemukan",
    "Tidak dapat mendemosikan pembuat obrolan",
    "Chat_admin_required",
    "Obrolan grup telah dinonaktifkan",
    "Metode hanya tersedia untuk obrolan grup super dan saluran",
    "Metode hanya tersedia untuk supergrup",
    "Perlu mengundang pengguna untuk menendang dari grup dasar",
    "Tidak cukup hak untuk membatasi / tidak membatasi anggota obrolan",
    "Tidak dalam obrolan",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Peer_id_invalid",
    "Pengguna adalah administrator obrolan",
    "Peserta_pengguna",
    "Pesan balasan tidak ditemukan",
    "Tidak dapat menghapus pemilik obrolan",
}

UNGBAN_ERRORS = {
    "Bot tidak dapat menambahkan anggota obrolan baru",
    "Channel_private",
    "Obrolan tidak ditemukan",
    "Tidak dapat mendemosikan pembuat obrolan",
    "Chat_admin_required",
    "Obrolan grup telah dinonaktifkan",
    "Metode hanya tersedia untuk obrolan grup super dan saluran",
    "Metode hanya tersedia untuk supergrup",
    "Perlu mengundang pengguna untuk menendang dari grup dasar",
    "Tidak cukup hak untuk membatasi / tidak membatasi anggota obrolan",
    "Tidak dalam obrolan",
    "Hanya pembuat grup dasar yang dapat menendang administrator grup",
    "Peer_id_invalid",
    "Pengguna adalah administrator obrolan",
    "User_not_participant",
    "Pesan balasan tidak ditemukan",
    "Pengguna tidak ditemukan",
}


@typing_action
def gban(update, context):
    message = update.effective_message
    chat = update.effective_chat
    args = context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    if user_id == OWNER_ID:
        message.reply_text("Usaha yang bagus -_- tapi aku tidak akan pernah memberinya.")
        return

    if int(user_id) in DEV_USERS:
        message.reply_text(
            "Whatt ... Bagaimana saya bisa gban seseorang yang merawat saya +_+"
        )
        return

    if int(user_id) in SUDO_USERS:
        message.reply_text(
            "Saya memata-matai, dengan mata kecil saya ... perang pengguna sudo! Mengapa kalian saling menyerang?"
        )
        return

    if int(user_id) in SUPPORT_USERS:
        message.reply_text(
            "OOOH seseorang mencoba memberi dukungan kepada pengguna! *meraih popcorn*"
        )
        return

    if user_id in (777000, 1087968824):
        message.reply_text(
            "Bagaimana saya bisa melarang seseorang yang saya tidak tahu siapa itu."
        )
        return

    if user_id == context.bot.id:
        message.reply_text(
            "-_- Lucu sekali, ayo gban sendiri kenapa tidak? Usaha yang bagus."
        )
        return

    if not reason:
        message.reply_text(
            "Harap sebutkan alasannya. Saya tidak akan mengizinkan gban :)"
        )
        return

    try:
        user_chat = context.bot.get_chat(user_id)
    except BadRequest as excp:
        message.reply_text(excp.message)
        return

    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if user_chat.first_name == "":
        message.reply_text(
            "Ini adalah akun yang telah dihapus! tidak ada gunanya memberi mereka..."
        )
        return

    if gban_db.is_user_gbanned(user_id):
        if not reason:
            message.reply_text(
                "Pengguna ini sudah diblokir; Saya akan mengubah alasannya, tetapi Anda belum memberi saya satu pun..."
            )
            return

        old_reason = gban_db.update_gban_reason(
            user_id, user_chat.username or user_chat.first_name, reason
        )
        user_id, new_reason = extract_user_and_text(message, args)

        if old_reason:
            banner = update.effective_user
            bannerid = banner.id
            bannername = banner.first_name
            new_reason = f"{new_reason} // GBanned oleh {bannername} banner id: {bannerid}"

            context.bot.sendMessage(
                GBAN_LOGS,
                "<b>Global Ban Reason Update</b>"
                "\n<b>Sudo Admin:</b> {}"
                "\n<b>User:</b> {}"
                "\n<b>ID:</b> <code>{}</code>"
                "\n<b>Previous Reason:</b> {}"
                "\n<b>New Reason:</b> {}".format(
                    mention_html(banner.id, banner.first_name),
                    mention_html(
                        user_chat.id, user_chat.first_name or "Deleted Account"
                    ),
                    user_chat.id,
                    old_reason,
                    new_reason,
                ),
                parse_mode=ParseMode.HTML,
            )

            message.reply_text(
                "Pengguna ini sudah diblokir, karena alasan berikut:\n"
                "<code>{}</code>\n"
                "Saya telah pergi dan memperbaruinya dengan alasan baru Anda!".format(
                    html.escape(old_reason)
                ),
                parse_mode=ParseMode.HTML,
            )

        else:
            message.reply_text(
                "Pengguna ini sudah diblokir, tetapi tidak ada alasan yang ditetapkan; Saya telah pergi dan memperbaruinya!"
            )

        return

    message.reply_text(
        f"<b>Pelarangan Global untuk</b> {mention_html(user_chat.id, user_chat.first_name)}"
        f"\n<b>ID Pengguna</b>: <code>{user_chat.id}</code>"
        f"\n<b>Alasan</b>: <code>{reason or 'Tidak ada alasan yang diberikan'}</code>",
        parse_mode=ParseMode.HTML,
    )

    banner = update.effective_user
    bannerid = banner.id
    bannername = banner.first_name
    reason = f"{reason} // GBanned oleh {bannername} banner id: {bannerid}"

    context.bot.sendMessage(
        GBAN_LOGS,
        "<b>New Global Ban</b>"
        "\n#GBAN"
        "\n<b>Status:</b> <code>Enforcing</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>"
        "\n<b>Reason:</b> {}".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name),
            user_chat.id,
            reason or "No reason given",
        ),
        parse_mode=ParseMode.HTML,
    )

    try:
        context.bot.kick_chat_member(chat.id, user_chat.id)
    except BadRequest as excp:
        if excp.message in GBAN_ERRORS:
            pass

    gban_db.gban_user(user_id, user_chat.username or user_chat.first_name, reason)


@typing_action
def ungban(update, context):
    message = update.effective_message
    args = context.args
    user_id = extract_user(message, args)
    if not user_id:
        message.reply_text("Anda sepertinya tidak mengacu pada pengguna.")
        return

    user_chat = context.bot.get_chat(user_id)
    if user_chat.type != "private":
        message.reply_text("Itu bukan pengguna!")
        return

    if not gban_db.is_user_gbanned(user_id):
        message.reply_text("Pengguna ini tidak dilarang!")
        return

    banner = update.effective_user

    message.reply_text(
        "Saya akan memberi {} kesempatan kedua, secara global.".format(user_chat.first_name)
    )

    context.bot.sendMessage(
        GBAN_LOGS,
        "<b>Regression of Global Ban</b>"
        "\n#UNGBAN"
        "\n<b>Status:</b> <code>Ceased</code>"
        "\n<b>Sudo Admin:</b> {}"
        "\n<b>User:</b> {}"
        "\n<b>ID:</b> <code>{}</code>".format(
            mention_html(banner.id, banner.first_name),
            mention_html(user_chat.id, user_chat.first_name),
            user_chat.id,
        ),
        parse_mode=ParseMode.HTML,
    )

    chats = get_all_chats()
    for chat in chats:
        chat_id = chat["chat_id"]

        # Check if this group has disabled gbans
        if not gban_db.does_chat_gban(chat_id):
            continue

        try:
            member = context.bot.get_chat_member(chat_id, user_id)
            if member.status == "kicked":
                context.bot.unban_chat_member(chat_id, user_id)

        except BadRequest as excp:
            if excp.message in UNGBAN_ERRORS:
                pass
            else:
                message.reply_text(
                    "Tidak dapat membatalkan gban karena: {}".format(excp.message)
                )
                context.bot.send_message(
                    OWNER_ID,
                    "Tidak dapat membatalkan gban karena: {}".format(excp.message),
                )
                return
        except TelegramError:
            pass

    gban_db.ungban_user(user_id)
    message.reply_text("Tidak di larang lagi.")


@send_action(ChatAction.UPLOAD_DOCUMENT)
def gbanlist(update, context):
    banned_users = gban_db.get_gban_list()

    if not banned_users:
        update.effective_message.reply_text(
            "Tidak ada pengguna yang dilarang! Anda lebih baik dari yang saya harapkan..."
        )
        return

    banfile = "List of retards.\n"
    for user in banned_users:
        banfile += "[x] {} - {}\n".format(user["name"], user["_id"])
        if user["reason"]:
            banfile += "Reason: {}\n".format(user["reason"])

    with BytesIO(str.encode(banfile)) as output:
        output.name = "gbanlist.txt"
        update.effective_message.reply_document(
            document=output,
            filename="gbanlist.txt",
            caption="Berikut adalah daftar pengguna yang diblokir saat ini.",
        )


def check_cas(user_id):
    cas_url = "https://api.cas.chat/check?user_id={}".format(user_id)
    try:
        r = get(cas_url, timeout=3)
        data = r.json()
    except BaseException:
        # LOGGER.info(f"CAS check failed for {user_id}")
        return False
    if data and data["ok"]:
        return "https://cas.chat/query?u={}".format(user_id)
    else:
        return False


def check_and_ban(update, user_id, should_message=True):
    try:
        spmban = spamwtc.get_ban(int(user_id))
        cas_banned = check_cas(user_id)

        if spmban or cas_banned:
            update.effective_chat.kick_member(user_id)
            if should_message:
                if spmban and cas_banned:
                    banner = "@Spamwatch and Combot Anti Spam"
                    reason = f"\n<code>{spmban.reason}</code>\n\nand <a href='{cas_banned}'>CAS Banned</a>"
                elif cas_banned:
                    banner = "Combot Anti Spam"
                    reason = f"<a href='{cas_banned}''>CAS Banned</a>"
                elif spmban:
                    banner = "@Spamwatch"
                    reason = f"<code>{spmban.reason}</code>"

                send_message(
                    update.effective_message,
                    "#SPAM_SHIELD\n\nOrang ini telah terdeteksi sebagai robot spam"
                    f"oleh {banner} dan telah dihapusd!\nAlasan: {reason}",
                    parse_mode=ParseMode.HTML,
                )
                return

    except Exception:
        pass

    if gban_db.is_user_gbanned(user_id):
        update.effective_chat.kick_member(user_id)
        if should_message:
            usr = gban_db.get_gbanned_user(user_id)
            greason = usr["reason"]
            if not greason:
                greason = "Tidak ada alasan yang diberikan"

            send_message(
                update.effective_message,
                f"*Waspada! pengguna ini telah diblokir dan telah dihapus!*\n*Alasan*: {greason}",
                parse_mode=ParseMode.MARKDOWN,
            )
            return


def enforce_gban(update, context):
    # Not using @restrict handler to avoid spamming - just ignore if cant gban.
    try:
        if (
            gban_db.does_chat_gban(update.effective_chat.id)
            and update.effective_chat.get_member(
                context.bot.id
            ).can_restrict_members
        ):
            user = update.effective_user
            chat = update.effective_chat
            msg = update.effective_message

            if user and not is_user_admin(chat, user.id):
                check_and_ban(update, user.id)

            if msg.new_chat_members:
                new_members = update.effective_message.new_chat_members
                for mem in new_members:
                    check_and_ban(update, mem.id)

            if msg.reply_to_message:
                user = msg.reply_to_message.from_user
                if user and not is_user_admin(chat, user.id):
                    check_and_ban(update, user.id, should_message=False)
    except (Unauthorized, BadRequest):
        pass


@user_admin
@typing_action
def gbanstat(update, context):
    args = context.args
    if len(args) > 0:
        if args[0].lower() in ["on", "yes"]:
            gban_db.enable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah mengaktifkan Spam Shield di grup ini. Ini akan membantu melindungi Anda "
                "dari spammer, karakter yang tidak menyenangkan, dan troll terbesar."
            )
        elif args[0].lower() in ["off", "no"]:
            gban_db.disable_gbans(update.effective_chat.id)
            update.effective_message.reply_text(
                "Saya telah menonaktifkan perisai Spam di grup ini. SpamShield tidak akan mempengaruhi pengguna Anda "
                "lagi. Anda akan kurang terlindungi dari troll dan spammer "
                "bagaimanapun juga!"
            )
    else:
        update.effective_message.reply_text(
            "Beri saya beberapa argumen untuk memilih pengaturan! on/off, yes/no!\n\n"
            "Pengaturan Anda saat ini adalah: {}\n"
            "Jika Benar, Semua Perisai Spam yang terjadi juga akan terjadi di grup Anda. "
            "Ketika Salah, mereka tidak akan melakukannya, meninggalkan Anda dengan kemungkinan belas kasihan "
            "oleh spammers.".format(gban_db.does_chat_gban(update.effective_chat.id))
        )


def __stats__():
    return "× {} gbanned users.".format(gban_db.num_gbanned_users())


def __user_info__(user_id):
    is_gbanned = gban_db.is_user_gbanned(user_id)
    spmban = spamwtc.get_ban(int(user_id))
    cas_banned = check_cas(user_id)

    text = "<b>Globally banned</b>: {}"

    if int(user_id) in DEV_USERS + SUDO_USERS + SUPPORT_USERS:
        return ""

    if user_id in (777000, 1087968824):
        return ""

    if cas_banned or spmban or is_gbanned:
        text = text.format("Yes")
        if is_gbanned:
            user = gban_db.get_gbanned_user(user_id)
            text += "\n<b>Alasan:</b> {}".format(html.escape(user["reason"]))
            text += "\nAjukan banding ke @Violet_Support jika menurut Anda itu tidak valid."
    else:
        text = text.format("No")
    return text


def __migrate__(old_chat_id, new_chat_id):
    gban_db.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    return "Obrolan ini berlaku *gbans*: `{}`.".format(
        gban_db.does_chat_gban(chat_id)
    )


__help__ = """
*Khusus Admin:*
 × /spamshield <on/off/yes/no>: Akan menonaktifkan atau mengaktifkan efek perlindungan Spam di grup Anda.

Perisai spam menggunakan Combot Anti Spam, @Spamwatch API dan larangan Global untuk menghapus Spammer sebanyak mungkin dari ruang obrolan Anda!

*Apa itu SpamWatch?*

SpamWatch menyimpan daftar larangan besar yang terus diperbarui dari robot spam, troll, pengirim spam bitcoin, dan karakter yang tidak menyenangkan.
KagaRobot akan terus membantu melarang spammer keluar dari grup Anda secara otomatis. Jadi, Anda tidak perlu khawatir spammer menyerbu grup Anda[.](https://telegra.ph/file/c1051d264a5b4146bd71e.jpg)
"""

__mod_name__ = "Spam Shield"

GBAN_HANDLER = CommandHandler(
    "gban",
    gban,
    pass_args=True,
    filters=CustomFilters.support_filter,
    run_async=True,
)
UNGBAN_HANDLER = CommandHandler(
    "ungban",
    ungban,
    pass_args=True,
    filters=CustomFilters.support_filter,
    run_async=True,
)
GBAN_LIST = CommandHandler(
    "gbanlist", gbanlist, filters=CustomFilters.support_filter, run_async=True
)

GBAN_STATUS = CommandHandler(
    "spamshield",
    gbanstat,
    pass_args=True,
    filters=Filters.chat_type.groups,
    run_async=True,
)

GBAN_ENFORCER = MessageHandler(
    Filters.all & Filters.chat_type.groups, enforce_gban, run_async=True
)

dispatcher.add_handler(GBAN_HANDLER)
dispatcher.add_handler(UNGBAN_HANDLER)
dispatcher.add_handler(GBAN_LIST)
dispatcher.add_handler(GBAN_STATUS)

if STRICT_GBAN:  # enforce GBANS if this is set
    dispatcher.add_handler(GBAN_ENFORCER, GBAN_ENFORCE_GROUP)
