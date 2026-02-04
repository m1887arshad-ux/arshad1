"""
Conversation State Management - Flexible Multi-Mode System

Replaces rigid FSM with layered intent architecture:
- Queries (ASK_*) can interrupt transactions
- Customer is optional
- Context preserved across mode switches
"""

class ConversationMode:
    """Bot conversation modes"""
    IDLE = "idle"
    BROWSING = "browsing"
    ORDERING = "ordering"
    CONFIRMING = "confirming"


class IntentType:
    """Intent hierarchy - priority order matters"""
    # Layer 1: Meta (highest priority)
    CANCEL = "cancel"
    HELP = "help"
    GREET = "greet"
    
    # Layer 2: Queries (reset order flow)
    ASK_STOCK = "ask_stock"
    ASK_SYMPTOM = "ask_symptom"
    ASK_PRICE = "ask_price"
    ASK_INFO = "ask_info"
    
    # Layer 3: Transactions
    START_ORDER = "start_order"
    PROVIDE_QUANTITY = "provide_quantity"
    PROVIDE_CUSTOMER = "provide_customer"
    CONFIRM_ORDER = "confirm_order"
    
    # Fallback
    UNKNOWN = "unknown"


# Query patterns that should interrupt order flow
QUERY_KEYWORDS = {
    "stock": ["hai kya", "available", "stock", "milega", "check", "?"],
    "symptom": ["bukhar", "fever", "dard", "pain", "cold", "sardi", "headache", "sir"],
    "price": ["kitne ka", "price", "cost", "kya rate"],
    "cancel": ["cancel", "stop", "band karo", "nahi", "mat karo"],
    "help": ["help", "kya kar", "batao", "kaise"],
}

# Transaction keywords (only relevant in flow)
TRANSACTION_KEYWORDS = {
    "order": ["chahiye", "order", "bill", "lena hai", "de do"],
    "confirm": ["confirm", "yes", "haan", "theek hai", "sahi hai", "ok"],
}
