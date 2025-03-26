import os
import argparse
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.errors import FloodWaitError
import asyncio
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Telegram Message Cleaner")
parser.add_argument("--api-id", required=True, help="Your Telegram API ID")
parser.add_argument("--api-hash", required=True, help="Your Telegram API Hash")
parser.add_argument("--dry-run", action="store_true", help="Simulate deletion without actually deleting messages")
args = parser.parse_args()

api_id = args.api_id
api_hash = args.api_hash
dry_run = args.dry_run

client = TelegramClient("default", api_id, api_hash)

async def clean(res, chatsn):
    for n in chatsn:
        c = res[n]
        count, name, messages, group = c[0], c[1], c[2], c[3]
        
        logger.info(f"Deleting {count} messages from {name}...")
        if dry_run:
            logger.info(f"Dry-run: Would delete {count} messages from {name}.")
            continue

        for i in range(0, len(messages), 100):  # Delete in batches of 100
            batch = messages[i:i + 100]
            try:
                await client.delete_messages(group, batch, revoke=True)
            except FloodWaitError as e:
                logger.warning(f"Rate limited. Waiting {e.seconds} seconds before retrying.")
                await asyncio.sleep(e.seconds)

async def main():
    logger.info("Telegram message cleaner")
    
    try:
        logger.info("Fetching dialogs...")
        dialogs = await client.get_dialogs(limit=None)
        groups = [i for i in dialogs if i.is_group]
        logger.info(f"Fetched {len(groups)} groups in total")
        
        me = await client.get_me()
        res = []
        for i in tqdm(groups, desc="Fetching messages"):
            messages = [msg.id for msg in await client.get_messages(i, limit=1000, from_user=me)]
            res.append((len(messages), i.name, messages, i))
        logger.info("Fetched messages from all groups.")
        
        res = sorted(res, key=lambda i: (-i[0], i[1]))
        logger.info("\nTop groups by message count:")
        for i, c in enumerate(res):
            logger.info(f"[{i}] {c[1]} - {c[0]} messages")

        try:
            delfrom = [int(i) for i in input("Enter group numbers to delete messages (e.g., 0 3 5): ").split()]
        except ValueError:
            logger.error("Invalid input. Please enter valid group numbers.")
            return
          
        confirm = input("Are you sure you want to delete all messages from the selected groups? (yes/no): ")
        if confirm.lower() == "yes":
            await clean(res, delfrom)
            logger.info("Done!")
        else:
            logger.info("Operation cancelled.")
    except Exception as e:
        logger.error(f"Error: {e}")

try:
    with client:
        client.loop.run_until_complete(main())
except KeyboardInterrupt:
    logger.info("Script interrupted by user.")
except Exception as e:
    logger.error(f"An error occurred: {e}")