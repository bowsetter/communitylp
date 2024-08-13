import asyncio
import os
import time

import gspread
import schedule
import telegram
from dateutil.parser import parse
from dateutil.utils import today
from dotenv import load_dotenv
from telegram.ext import Updater
from telegram import ParseMode, ChatMember

import google_table_helper
from google_table_helper import GOOGLE_JSON

# Load dotenv (config from .env file)
load_dotenv()

# Create the Updater and pass it your bot's token.
updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

# Get the dispatcher to register handlers
app = updater.dispatcher

# Create Google connection
gc = gspread.service_account(GOOGLE_JSON)

# Open a sheet from a spreadsheet in one go
wks = gc.open(os.getenv("GOOGLE_TABLE_NAME")).sheet1

messages_templates = google_table_helper.google_table_get_message_templates()


def main():
    cell = wks.get_all_values()

    payments = google_table_helper.purge_cache_google_tabel_and_update()

    for paymentRaw in payments:
        user_id = paymentRaw[0]
        dt = parse(paymentRaw[1])

        if today().date() > dt.date():
            try:
                member = app.bot.get_chat_member(
                    chat_id=os.getenv("TELEGRAM_GROUP_ID"),
                    user_id=user_id,
                )

                try:
                    app.bot.send_message(
                        chat_id=user_id,
                        text=messages_templates[3][0],
                        parse_mode=ParseMode.HTML
                    )

                except Exception as e:
                    print(e.__traceback__)

                if member and member.status == ChatMember.MEMBER:
                    app.bot.ban_chat_member(
                        chat_id=os.getenv("TELEGRAM_GROUP_ID"),
                        user_id=user_id,
                    )

                    app.bot.send_message(
                        chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                        text="💳 <b>Customer did not make payment</b>\n\n"
                             "Client excluded from groups for non-payment of access to it"
                             f"\n\n\nThe customer ID: {user_id}"
                             f"\nClient: {member.user.mention_html()}",
                        parse_mode=ParseMode.HTML
                    )

            except telegram.error.BadRequest:
                try:
                    app.bot.send_message(
                        chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                        text="💳 <b>Customer did not make payment</b>\n\n"
                             "Client excluded from groups for non-payment of access to it"
                             f"\n\n\nThe customer ID: {user_id}",
                        parse_mode=ParseMode.HTML
                    )

                except Exception as e:
                    print(e.__traceback__)

            finally:
                for i, row in enumerate(cell):
                    if row == paymentRaw:
                        del cell[i]

    wks.clear()
    wks.update('A1', cell)


def job():
    try:
        main()
    except Exception as e:
        print(e.__traceback__)


if __name__ == '__main__':
    print("Cron JOB")

    schedule.every(15).minutes.do(job)

    while True:
        schedule.run_pending()
        time.sleep(15)
