# Fiver's info:
#   Delivery date: 17 Nov, 2:40
#   Total price: US$30
#   Order number: #FO2A92EE1F42 / fo2a92ee1f42
#
# Props:
#   Observer Bot Token: 5681843713:AAEN2_dHcpBLxfocZ7s03MNy6xEpP6nuYRI
#   Main Bot Token: 5747868344:AAFxizn3pzLB-0xO13A31zQ62GlhM_qbMto
#   AppID (Telegram APP): 28198358
#   AppHash (Telegram APP): d3c632bb680e0409603f5b5ce3045d56

import json
import logging
import multiprocessing
import os.path
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process

import dotenv
from dateutil.parser import parse
from dateutil.utils import today
from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.handlers import ChatMemberUpdatedHandler
from telegram import ForceReply, Update, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, Updater, Filters

import google_table_helper

# Load dotenv (config from .env file)
load_dotenv()

# Pyrogram application
api_id = 3380669
api_hash = "ec5acfb149e195c7659a1bf894b3284d"

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Create logger
logger = logging.getLogger(__name__)

# Create the Updater and pass it your bot's token.
updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

# Get the dispatcher to register handlers
app = updater.dispatcher

sessions = {
    'wait_trx_id': [],
    'pay_wait_response': [],
}

messages_templates = google_table_helper.google_table_get_message_templates()


# Define a few command handlers.
# These usually take the two arguments update and context.
def start_command(update: Update, context) -> None:
    """Send a message when the command /start is issued."""

    if context:

         keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    text="Tap HERE after payment",
                    callback_data=f"command_pay:{update.effective_message.chat_id}"
                )
            ]
        ])
         context.bot.send_message(
                chat_id=update.effective_message.chat_id,
                text= messages_templates[0][0],
                disable_web_page_preview=True,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
  
      


# Define a few command handlers.
# These usually take the two arguments update and context.
def help_command(update: Update, context) -> None:
    """Send a message when the command /help is issued."""

    if context:
        update.message.reply_text(
            messages_templates[2][0]
        )


# Define a few command handlers.
# These usually take the two arguments update and context.
def purge_cache_command(update: Update, context) -> None:
    global messages_templates

    """Send a message when the command /purge is issued."""

    if context:

        update.message.reply_text(
            f"💧 Refreshing ..."
        )

        google_table_helper.purge_cache_google_tabel_and_update()
        messages_templates = google_table_helper.google_table_get_message_templates()

        update.message.reply_text(
            f"💧 Refreshed ({len(messages_templates)})"
        )


def transfer_admin_command(update: Update, context) -> None:
    """Send a message when the command /transfer_admin is issued."""
    user = update.effective_user

    if str(user.id) != os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
        return

    user_id = update.message.text.replace("/transfer_admin ", "")

    if context:
        update.message.reply_text(
            f"🕔 Waiting for confirmation from the user"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    text="Approve",
                    callback_data=f"approve_admin_transfer:{user_id}"
                )
            ]
        ])

        try:
            context.bot.send_message(
                chat_id=user_id,
                text="🔽 <b>You have received an offer to transfer administrator rights to you.</b>\n\n"
                     "To accept it, click the button below the offer or just ignore the message",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        except Exception as e:
            print(e.__traceback__)


def set_channel_command(update: Update, context) -> None:
    """Send a message when the command /set_channel is issued."""
    user = update.effective_user

    if str(user.id) != os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
        return

    channel_id = update.message.text.replace("/set_channel ", "")

    if context:
        os.unsetenv("TELEGRAM_GROUP_ID")
        os.putenv("TELEGRAM_GROUP_ID", (channel_id))

        os.environ["TELEGRAM_GROUP_ID"] = (channel_id)

        dotenv.set_key(".env", "TELEGRAM_GROUP_ID", os.environ["TELEGRAM_GROUP_ID"])

        update.message.reply_text(
            f"🆙 We are now working with the channel: {channel_id}"
        )


# Define a few command handlers.
# These usually take the two arguments update and context.
def pay_command(update: Update, context) -> None:
    """Send a message when the command /pay is issued."""
    query = update.callback_query
    text = update.callback_query.data
    user_id = text.replace("command_pay:", "")
    if context:
        user = update.effective_user

        users_in_expire_table = google_table_helper.read_local_json_cache()

        if str(user.id) in sessions.get("pay_wait_response", []):
            update.message.reply_html(
                "🕧 <b>Your application is being verified</b>.\n\n"
                "It will not take long, please wait.\n"
                "You will receive an answer as soon as we have checked everything"
            )

            return

        # Example stack:
        #
        # [
        #    ["{user_id: string}", "{date: string}"],
        #    ["{user_id: string}", "{date: string}"],
        #    ["{user_id: string}", "{date: string}"],
        #
        #    ...
        # ]
        users_with_active_subscribe = list(filter(
            # Function
            lambda row: parse(row[1]) >= today(),

            # List
            users_in_expire_table
        ))

        # Example stack:
        #
        # [
        #    "{user_id: string}",
        #    "{user_id: string}",
        #    "{user_id: string}",
        #
        #    ...
        # ]
        users_ids_with_active_subscribe = list(map(
            # Function
            lambda r: str(r[0]),

            # List
            users_with_active_subscribe
        ))

        if str(user.id) in users_ids_with_active_subscribe:
              context.bot.send_message(
              chat_id=query.message.chat_id,
              text="You already have access to the channel",
              parse_mode=ParseMode.HTML
              )
              return

        # Expect to hear from user TRX
        sessions["wait_trx_id"].append(int(user_id))

    
        context.bot.send_message(
        chat_id=query.message.chat_id,
        text="Reply below with your transaction number.",
        parse_mode=ParseMode.HTML,
        reply_markup=ForceReply(
                selective=True
            )
        )
        

# Get user/chat ID
# Work only with admin
def id_command(update: Update, context) -> None:
    """Send a message when the command /id is issued."""

    if context:
        user = update.effective_user

        if str(user.id) == os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
            update.message.reply_html(
                rf"Hi {user.mention_html()}! ID: {update.message.chat_id}"
            )


# Function for handling /pay
# commands and channel/chat join events
# The work algorithm is as follows
#
#   command:/pay -> action:message;
#
#     AND
#
#   action:member_activity;
def message_handler(update, context: ContextTypes.context):
   
    # No one message
    # (posted message in channel)
    if not update.message:
        return

    # If there is an open session where
    # we are waiting for a message from
    # a user with transaction data
    if update.message.from_user.id in sessions.get("wait_trx_id"):
        sessions["wait_trx_id"].remove(update.message.from_user.id)
        sessions["pay_wait_response"].append(str(update.message.from_user.id))

        user = update.message.from_user

        # Sending the report to
        # the administrator
        if os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        text="Approve",
                        callback_data=f"approve_payment:{update.message.from_user.id},{user.username},{update.message.text}"
                    ),
                    InlineKeyboardButton(
                        text="...",
                        callback_data="no_one"
                    ),
                    InlineKeyboardButton(
                        text="...",
                        callback_data="no_one"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="...",
                        callback_data="no_one"
                    ),
                    InlineKeyboardButton(
                        text="...",
                        callback_data="no_one"
                    ),
                    InlineKeyboardButton(
                        text="Reject",
                        callback_data=f"reject_payment:{update.message.from_user.id}"
                    )
                ]
            ])

            context.bot.send_message(
                chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                text="💸️ <b>Payment Verification Request</b>\n\n"
                     "The user asks to verify the fact of payment"
                     f"\n\n\nUsername: {user.username}"
                     f"\nUser ID: {user.id}"
                     f"\nUser: {user.mention_html()}"
                     f"\nTRX: {update.message.text}",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        update.message.reply_html(
            f"⏳ Request has been sent!\n\nWe will notify you as soon as we verify the payment.",
        )

        return

    # The event is not an event
    # related to a member of the group
    if not update.message.new_chat_members:
        return

    new_members = update.message.new_chat_members

    if new_members:
        users_in_expire_table = []

        if os.path.isfile("SheetLiveCache.json"):
            users_in_expire_table = json.loads(open("SheetLiveCache.json", "r+").read())

        for user in new_members:
            if user.is_bot:
                continue

            # Example stack:
            #
            # [
            #    ["{user_id: string}", {access_allow: bool}],
            #    ["{user_id: string}", {access_allow: bool}],
            #    ["{user_id: string}", {access_allow: bool}],
            #
            #    ...
            # ]
            users_with_access_rights = list(map(lambda u: [u[0], parse(u[1]) >= today()], users_in_expire_table))

            # Example stack:
            #
            # [
            #    ["{user_id: string}", False]
            #
            #    ...
            # ]
            users_with_no_access = (list(filter(lambda x: not x[1], users_with_access_rights)))

            # Example stack:
            #
            # [
            #   "{user_id: string}",
            #   "{user_id: string}",
            #   "{user_id: string}",
            #
            #   ...
            # ]
            only_user_id_in_expire_table = list(map(lambda x: str(x[0]), users_in_expire_table))

            # Example stack:
            #
            # [
            #   "{user_id: string}",
            #   "{user_id: string}",
            #   "{user_id: string}",
            #
            #   ...
            # ]
            only_user_id_with_no_access = (list(map(lambda x: str(x[0]), users_with_no_access)))

            if str(user.id) in only_user_id_in_expire_table:
                if not str(user.id) in only_user_id_with_no_access:
                    continue

            # There no reason to skip.
            # Blocking access to the group
            try:
                context.bot.send_message(
                    user.id,
                    str(messages_templates[1][0]),
                    parse_mode=ParseMode.HTML
                )

                context.bot.ban_chat_member(
                    chat_id=update.message.chat.id,
                    user_id=user.id,
                )

            except Exception as e:
                me = context.bot.get_me()

                message = update.message.reply_text(
                    "To get access to the channel, "
                    "you must renew or pay for a subscription.\n\n"
                    f"Read more: @{me.username}"
                )

                context.bot.ban_chat_member(
                    chat_id=update.message.chat.id,
                    user_id=user.id,
                )

                if message:
                    context.bot.delete_message(
                        chat_id=update.message.chat.id,
                        message_id=message.message_id
                    )

            finally:
                if os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
                    context.bot.send_message(
                        chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                        text="⚠️ <b>Auth request</b>\n\n"
                             "User just tried to enter your private chat, but it was not authorized in the bot, "
                             "so the user did not get a message to pay for access. "
                             "\n\nContact him personally to "
                             "clarify the details"
                             f"\n\n\nUsername: {user.username}"
                             f"\nUser ID: {user.id}"
                             f"\nUser: {user.mention_html()}",
                        parse_mode=ParseMode.HTML
                    )


# Actions
#   - Approve payment
#      regex: approve_payment:{user_id}
#      behavior:
#          1. Adds data to the Google Table.
#          2. Sends a message to the user about successful payment.
#          3. Removes the confirmation message from the administrator

# Action reject payment
def action_approve_admin_transfer(update: Update, context):
    query = update.callback_query
    text = update.callback_query.data
    user_id = text.replace("approve_admin_transfer:", "")

    os.unsetenv("TELEGRAM_ADMIN_CHAT_ID")
    os.putenv("TELEGRAM_ADMIN_CHAT_ID", (user_id))

    os.environ["TELEGRAM_ADMIN_CHAT_ID"] = (user_id)

    dotenv.set_key(".env", "TELEGRAM_ADMIN_CHAT_ID", os.environ["TELEGRAM_ADMIN_CHAT_ID"])

    context.bot.send_message(
        chat_id=query.message.chat_id,
        text="<b>👌 Transfer of Rights </b>\n\n"
             f"you are now the new administrator of this bot  ",
        parse_mode=ParseMode.HTML
    )

    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )


def action_reject(update: Update, context):
    query = update.callback_query
    text = update.callback_query.data
    user_id = text.replace("reject_payment:", "")

    context.bot.send_message(
        chat_id=user_id,
        text="<b>😞 We did not receive payment from you</b>\n\n"
             f"Unfortunately, your payment has not been received by us."
             f" You probably entered incorrect data about the payment, "
             f" or you made a mistake in the details."
             f" If you think this is a mistake, "
             f"please contact us as soon as possible ",
        parse_mode=ParseMode.HTML
    )

    context.bot.delete_message(
        chat_id=query.message.chat_id,
        message_id=query.message.message_id
    )

    if user_id in sessions["pay_wait_response"]:
        sessions["pay_wait_response"].remove(user_id)


# Action approve payment
def action_approve(update: Update, context):
    query = update.callback_query
    text = update.callback_query.data
    userdata = text.replace("approve_payment:", "")
    x = userdata.split(",")
 
    user_id = x[0]
    username = x[1]
    mpesa_id = x[2]

    end_date = today() + timedelta(
        days=int(os.getenv("SUBSCRIPTION_RENEWAL_TIME_IN_DAYS"))
    )

    # Adding information
    # to the Google Table
    #
    # Python array:
    #   [
    #       "{user_id}",
    #       "{date}"
    #   ]
    #
    # looks like as:
    #
    #       A        B
    # 1 {user_id}  {date}
    # 2 {user_id}  {date}
    # 3 {user_id}  {date}
    #
    # in google table
    google_table_helper.wks.append_row(
        [
            user_id,
            end_date.date().strftime("%Y.%m.%d")
        ]
    )

    google_table_helper.recwhole.append_row(
        [
            username,
            user_id,
            mpesa_id,
            end_date.date().strftime("%Y.%m.%d")
        ]
    )

    # Refreshing the cache
    google_table_helper.purge_cache_google_tabel_and_update()

    try:
        context.bot.unban_chat_member(
            os.getenv("TELEGRAM_GROUP_ID"),
            user_id
        )

    except Exception as e:
        print(e.__traceback__)

    link = context.bot.create_chat_invite_link(
        os.getenv("TELEGRAM_GROUP_ID"),
        datetime.today() + timedelta(hours=12),
        member_limit=1
    )

    if link.invite_link:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text="✅ <b>Payment was successful!</b>\n\n"
                     f"Keep the link to the channel!\n\n"
                     f"Link: {link.invite_link}\n"
                     f"Warning! The link is valid for 12 hours and only for one user ",
                parse_mode=ParseMode.HTML
            )

            context.bot.delete_message(
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )

        except Exception:
            context.bot.send_message(
                chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                text="⛔ <b>Warning!</b>\n\n"
                     "The user did not receive an invitation link!"
                     f"send it to him manually: {link.invite_link}",
                parse_mode=ParseMode.HTML
            )

    else:
        context.bot.send_message(
            chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
            text="⛔ <b>Warning!</b>\n\n"
                 "The bot was unable to create an invitation link automatically."
                 "You will have to manually invite the user to the group."
                 "\n\nCheck the rights granted to the bot",
            parse_mode=ParseMode.HTML
        )

    if user_id in sessions["pay_wait_response"]:
        sessions["pay_wait_response"].remove(user_id)

    context.bot.answer_callback_query(query.id, "🟢 APPROVED")


def main():
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("pay", pay_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("purge", purge_cache_command))
    app.add_handler(CommandHandler("transfer_admin", transfer_admin_command))
    app.add_handler(CommandHandler("set_channel", set_channel_command))

    app.add_handler(
        CallbackQueryHandler(action_approve, pattern="approve_payment:(.*?)")
    )

    app.add_handler(
        CallbackQueryHandler(action_reject, pattern="reject_payment:(.*?)")
    )

    app.add_handler(
        CallbackQueryHandler(action_approve_admin_transfer, pattern="approve_admin_transfer:(.*?)")
    )

    app.add_handler(
        CallbackQueryHandler(pay_command, pattern="command_pay:(.*?)")
    )

    # handler to process new member event
    app.add_handler(MessageHandler(Filters.all, message_handler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


# handler for
async def chatMemberUpdatedHandler(client, message):
    new_member = message.new_chat_member

    if not new_member:
        return

    if new_member.status == ChatMemberStatus.MEMBER:
        users_in_expire_table = []

        if os.path.isfile("SheetLiveCache.json"):
            users_in_expire_table = json.loads(open("SheetLiveCache.json", "r+").read())

        blocked_users = (list(filter(lambda x: x[1] == False,
                                     list(map(lambda r: [r[0], parse(r[1]) >= today()], users_in_expire_table)))))

        if str(new_member.user.id) in list(map(lambda x: x[0], users_in_expire_table)):
            if not str(new_member.user.id) in (list(map(lambda x: x[0], blocked_users))):
                return

        await client.ban_chat_member(
            int(os.getenv("TELEGRAM_GROUP_ID")),
            new_member.user.id
        )

        try:
            await app.bot.send_message(
                new_member.user.id,
                str(messages_templates[1][0]),
                parse_mode=ParseMode.HTML
            )

        except Exception as e:
            print(e.__traceback__)

        finally:
            if os.getenv("TELEGRAM_ADMIN_CHAT_ID"):
                await app.bot.send_message(
                    chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                    text="⚠️ <b>Auth request</b>\n\n"
                         "User just tried to enter your private chat, but it was not authorized in the bot, "
                         "so the user did not get a message to pay for access. "
                         "\n\nContact him personally to "
                         "clarify the details"
                         f"\n\n\nUsername: @{new_member.user.username}"
                         f"\nUser ID: {new_member.user.id}",
                    parse_mode=ParseMode.HTML
                )


def channel_main():
    client = Client("observer", api_id, api_hash, bot_token=os.getenv("TELEGRAM_BOT_OBSERVER_TOKEN"))

    client.add_handler(ChatMemberUpdatedHandler(chatMemberUpdatedHandler))

    client.run()


class HttpGetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write('{}'.encode())


def run(server_class=HTTPServer, handler_class=BaseHTTPRequestHandler):
    if os.getenv("PORT"):
        server_address = ('', int(os.getenv("PORT")))
        httpd = server_class(server_address, handler_class)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.server_close()

        print("Start app on " + os.getenv("PORT") + " port")


if __name__ == '__main__':
    if not os.path.isfile("SheetLiveCache.json"):
        open("SheetLiveCache.json", "w+").write("{}")

    http_job_thread = multiprocessing.Process(target=run, args=(HTTPServer, HttpGetHandler))
    http_job_thread.start()

    # If channel mode
    if os.getenv("TELEGRAM_MODE") == "CHANNEL":
        Process(target=main).start()
        Process(target=channel_main).start()

    # If group mode
    if os.getenv("TELEGRAM_MODE") == "GROUP":
        main()
