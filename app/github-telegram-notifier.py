import aiohttp
import asyncio
import json
import logging
import os
import signal
import sys
import telegram

# Define secrets
GH_TOKEN = os.getenv("GH_TOKEN")
if GH_TOKEN is None:
    raise ValueError("GH_TOKEN environment variable must be set")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if TELEGRAM_TOKEN is None:
    raise ValueError("TELEGRAM_TOKEN environment variable must be set")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if TELEGRAM_CHAT_ID is None:
    raise ValueError("TELEGRAM_CHAT_ID environment variable must be set")

GH_API_URL = os.getenv("GH_API_URL", "https://api.github.com")

# Define the path to the file that stores the IDs of the notifications that have already been sent
NOTIFICATIONS_FILE = os.getenv("NOTIFICATIONS_FILE", "state/notifications.json")
NOTIFICATIONS_DIRECTORY = os.path.dirname(NOTIFICATIONS_FILE)

# Set log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


# Set up logging
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s %(levelname)s:%(message)s")

# Set up state
if not os.path.exists(NOTIFICATIONS_DIRECTORY):
    os.makedirs(NOTIFICATIONS_DIRECTORY)


async def fetch_notifications(session, url, headers):
    """Fetches the unread notifications from the GitHub API."""
    async with session.get(url, headers=headers) as response:
        if response.status == 200:
            return await response.json()
        else:
            logging.error(
                f"Failed to fetch notifications from GitHub API: {response.status}"
            )


def get_unread_notifications(notifications):
    """Filters the notifications to only include unread ones."""
    return [n for n in notifications if "unread" in n and n["unread"]]


def load_notifications():
    """Loads the IDs of the notifications that have already been sent from the notifications file."""
    if os.path.isfile(NOTIFICATIONS_FILE):
        with open(NOTIFICATIONS_FILE, "r") as f:
            return set(json.load(f))
    else:
        return set()


def save_notifications(notifications):
    """Saves the IDs of the notifications that have already been sent to the notifications file."""
    with open(NOTIFICATIONS_FILE, "w") as f:
        json.dump(list(notifications), f)


async def send_telegram_message(message):
    """Sends a message to the specified Telegram chat."""
    bot = telegram.Bot(TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


async def main(session):
    headers = {"Authorization": f"Bearer {GH_TOKEN}"}
    url = f"{GH_API_URL}/notifications"
    notifications = await fetch_notifications(session, url, headers)
    unread_notifications = get_unread_notifications(notifications)
    sent_notifications = load_notifications()
    new_notifications = [
        n for n in unread_notifications if str(n["id"]) not in sent_notifications
    ]
    for n in new_notifications:
        message = f"{n['subject']['title']} ({n['repository']['full_name']})"
        logging.info(f"New notification: {message}")
        await send_telegram_message(message)
        sent_notifications.add(str(n["id"]))
    save_notifications(sent_notifications)


async def run():
    async with aiohttp.ClientSession() as session:
        while True:
            await main(session)
            await asyncio.sleep(10)


def handle_sigterm(signal, frame):
    logging.info("Received SIGTERM signal, stopping...")
    sys.exit(0)


if __name__ == "__main__":
    # Register SIGTERM handler
    signal.signal(signal.SIGTERM, handle_sigterm)
    logging.info("Starting GitHub Telegram Notifier")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logging.info("Shutting down GitHub Telegram Notifier...")
    except Exception as e:
        logging.exception("Unhandled exception in main loop")
        raise e
    logging.info("GitHub Telegram Notifier finished successfully")
