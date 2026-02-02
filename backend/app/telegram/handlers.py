"""
Telegram message handler: parse intent (rule-based), create DRAFT, reply.
NO EXECUTION FROM TELEGRAM. NO AUTONOMY.
"""
from telegram import Update
from telegram.ext import ContextTypes

from app.db.session import SessionLocal
from app.models.business import Business
from app.agent.decision_engine import validate_and_create_draft


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On incoming message: parse -> create AgentAction DRAFT -> reply. Owner must approve from dashboard."""
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    db = SessionLocal()
    try:
        # Find business linked to this Telegram chat
        business = db.query(Business).filter(Business.telegram_chat_id == str(chat_id)).first()
        if not business:
            # Hackathon: optionally link first business for demo
            business = db.query(Business).first()
        if not business:
            await update.message.reply_text(
                "No business linked to this chat. Please link Telegram from Owner Dashboard first."
            )
            return

        draft = validate_and_create_draft(db, business.id, text, telegram_chat_id=str(chat_id))
        if draft:
            await update.message.reply_text(
                "Action drafted. Please approve from Owner Dashboard."
            )
        else:
            await update.message.reply_text(
                "Could not understand. Try: 'Rahul ko 500 ka bill bana do' or '500 ka invoice Rahul'"
            )
    finally:
        db.close()
