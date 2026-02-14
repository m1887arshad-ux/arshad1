import asyncio
import threading
import time
from typing import Optional

from telegram import error
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from app.core.config import settings
from app.telegram.handlers_refactored import handle_message_refactored as handle_message, handle_start
from app.telegram.handlers_photo import handle_photo_message

_bot_app: Optional[Application] = None

async def _start_polling_with_retry(app, max_retries=3, initial_backoff=2):
    for attempt in range(max_retries):
        try:
            print(f"[Telegram] Starting polling (attempt {attempt + 1}/{max_retries})...")
            await app.updater.start_polling(drop_pending_updates=True)
            print("[Telegram] ✓ Polling started successfully")
            return True
        except error.Conflict as e:
            if attempt < max_retries - 1:
                backoff = initial_backoff * (2 ** attempt)
                print(f"[Telegram] ⚠ Conflict detected: {e}")
                print(f"[Telegram] Retrying in {backoff}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(backoff)
            else:
                print(f"[Telegram] ✗ Failed after {max_retries} retries. Bot disabled.")
                print(f"[Telegram] Error: {e}")
                return False
        except Exception as e:
            print(f"[Telegram] Unexpected error: {e}")
            return False


def _run_bot():
    global _bot_app
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        _bot_app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Add command handler for /start
        _bot_app.add_handler(CommandHandler("start", handle_start))
        _bot_app.add_handler(CommandHandler("start", handle_start))
        _bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))
        # Start polling in the event loop
        loop.run_until_complete(_bot_app.initialize())
        loop.run_until_complete(_bot_app.start())
        
        # Try to start polling with retries
        loop.run_until_complete(_bot_app.initialize())
        loop.run_until_complete(_bot_app.start())
        
        loop.run_forever()
    except Exception as e:
        print(f"Telegram bot error: {e}")
    finally:
        try:
            if _bot_app:
                loop.run_until_complete(_bot_app.shutdown())
        except Exception:
            pass
        loop.close()


def start_bot_background():
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    t = threading.Thread(target=_run_bot, daemon=True)
    t.start()


def stop_bot_background():
    """Stop polling. Called on FastAPI shutdown."""
    # Bot runs in daemon thread, will be killed when main process exits
    pass


async def send_telegram_message(chat_id: int | str, message: str) -> bool:
    """
    Send a message to a Telegram chat
    
    Args:
        chat_id: Telegram chat ID
        message: Message text to send
        
    Returns:
        True if sent successfully, False otherwise
    """
    global _bot_app
    
    if not _bot_app:
        print("Telegram bot not initialized")
        return False
    
    try:
        await _bot_app.bot.send_message(
            chat_id=int(chat_id),
            text=message,
            parse_mode='Markdown'
        )
        return True
    except Exception as e:
        print(f"Failed to send Telegram message to {chat_id}: {e}")
        return False
