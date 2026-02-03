"""
Rule-based intent parsing. NO AI.
Handles simple Hinglish/English patterns for invoice/bill creation.
Future: LLM-based Hinglish understanding will be added here later (comment only; do not import AI).
"""
import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class ParsedIntent:
    intent: str  # e.g. create_invoice, send_reminder
    payload: dict  # customer_name, amount, channel, etc.


# Invoice Patterns: "Rahul ko 500 ka bill bana do", "500 ka invoice Rahul"
INVOICE_PATTERNS = [
    re.compile(r"(?P<name>[\w\s]+)\s+ko\s+(?P<amount>[\d.]+)\s+ka\s+(bill|invoice)", re.IGNORECASE),
    re.compile(r"(?P<amount>[\d.]+)\s+ka\s+(bill|invoice)\s+(?P<name>[\w\s]+)", re.IGNORECASE),
    re.compile(r"(bill|invoice)\s+(?:for|bana do)\s+(?P<name>[\w\s]+)\s+(?P<amount>[\d.]+)", re.IGNORECASE),
    re.compile(r"(?P<amount>[\d.]+)\s+(?:ka\s+)?invoice\s+(?P<name>[\w\s]+)", re.IGNORECASE),
    re.compile(r"invoice\s+(?P<name>[\w\s]+)\s+(?P<amount>[\d.]+)", re.IGNORECASE),
]

# Stock Check Patterns: "kya Crocin stock mein hai", "Dolo available hai kya", "check Paracetamol"
STOCK_CHECK_PATTERNS = [
    re.compile(r"(?:kya|check|verify)\s+(?P<item>[\w\s\(\)]+?)\s+(?:stock|available|hai|milega)", re.IGNORECASE),
    re.compile(r"(?P<item>[\w\s\(\)]+?)\s+(?:stock|available|milega)\s+(?:hai|kya|mein)", re.IGNORECASE),
    re.compile(r"(?:hai|milega)\s+(?:kya\s+)?(?P<item>[\w\s\(\)]+?)\s*\??$", re.IGNORECASE),
    re.compile(r"^(?P<item>[\w\s\(\)]+?)\s+(?:hai|available|stock)\s*\??$", re.IGNORECASE),
]


def parse_message(text: str) -> Optional[ParsedIntent]:
    """
    Rule-based parse. Returns structured intent + entities or None if no match.
    Supports: invoices, stock checks.
    No AI. No LLM. Clear hooks for future LLM replacement.
    """
    if not text or not text.strip():
        return None
    text = text.strip()

    # Try Stock Check patterns first
    for pattern in STOCK_CHECK_PATTERNS:
        m = pattern.search(text)
        if m:
            item = (m.group("item") or "").strip()
            if item and len(item) > 2:  # At least 3 chars
                return ParsedIntent(
                    intent="check_stock",
                    payload={
                        "item_name": item,
                        "action_type": "StockCheck",
                        "channel": "WhatsApp",
                    },
                )

    # Try Invoice patterns
    for pattern in INVOICE_PATTERNS:
        m = pattern.search(text)
        if m:
            g = m.groupdict()
            name = (g.get("name") or "").strip()
            amount_str = g.get("amount") or "0"
            try:
                amount = float(amount_str.replace(",", ""))
            except ValueError:
                amount = 0.0
            if name and amount > 0:
                return ParsedIntent(
                    intent="create_invoice",
                    payload={
                        "customer_name": name,
                        "amount": amount,
                        "action_type": "Invoice",
                        "channel": "WhatsApp",
                    },
                )

    # Fallback: "500 Rahul" or "Rahul 500"
    simple = re.match(r"^(?P<name>[\w\s]+)\s+(?P<amount>[\d.]+)$", text.strip())
    if simple:
        g = simple.groupdict()
        name = (g.get("name") or "").strip()
        try:
            amount = float((g.get("amount") or "0").replace(",", ""))
        except ValueError:
            amount = 0.0
        if name and amount > 0:
            return ParsedIntent(
                intent="create_invoice",
                payload={
                    "customer_name": name,
                    "amount": amount,
                    "action_type": "Invoice",
                    "channel": "WhatsApp",
                },
            )

    return None
