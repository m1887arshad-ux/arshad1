"""
Telegram Photo Handler: OCR functionality temporarily disabled

Note: Prescription image processing is currently disabled.
Users should enter medicines manually via text chat.
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle prescription/bill image uploads from Telegram.
    
    OCR functionality is currently disabled. Users should enter orders manually.
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    logger.info(
        f"[TELEGRAM PHOTO] Received photo from user_id={user_id}, "
        f"chat_id={chat_id} - OCR disabled, returning instruction message"
    )
    
    # Return helpful message directing user to text-based ordering
    await update.message.reply_text(
        "📷 Image received\n\n"
        "⚠️ Prescription image processing is temporarily disabled.\n\n"
        "Please enter your medicine order manually in text format:\n\n"
        "Example:\n"
        "• \"I need 2 Paracetamol\"\n"
        "• \"Order 5 Crocin for Rahul\"\n"
        "• \"10 Benadryl\"\n\n"
        "I'll guide you through the order step by step! 💊"
    )
    
    logger.info(f"[TELEGRAM PHOTO] Sent OCR disabled message to chat_id={chat_id}")
