import re
import os
import json
from datetime import date, datetime, timedelta
from models.category import Category

# Comprehensive keyword lexicon for zero-dependency instant categorization
CATEGORY_KEYWORD_MAP = {
    "Food & Dining": [
        "dinner", "lunch", "breakfast", "brunch", "coffee", "cafe", "restaurant", "bistro",
        "kfc", "mcdonalds", "starbucks", "subway", "pizza", "burger", "sushi", "taco",
        "chipotle", "dominos", "dunkin", "bakery", "bar", "pub", "brewery", "grill",
        "ubereats", "doordash", "grubhub", "zomato", "swiggy", "eating", "food"
    ],
    "Groceries": [
        "grocery", "groceries", "supermarket", "walmart", "target", "costco", "trader joe",
        "whole foods", "safeway", "aldi", "kroger", "vegetables", "fruits", "milk", "bread",
        "market", "spices", "provisions", "mart"
    ],
    "Housing & Rent": [
        "rent", "mortgage", "apartment", "landlord", "property", "hoa", "housing", "lease"
    ],
    "Utilities & Bills": [
        "electricity", "power", "water", "gas bill", "utility", "internet", "wifi", "broadband",
        "sewage", "trash", "phone bill", "mobile", "verizon", "att", "tmobile", "electric"
    ],
    "Transportation & Fuel": [
        "uber", "lyft", "taxi", "cab", "gas", "gasoline", "fuel", "petrol", "diesel", "shell",
        "chevron", "bp", "exxon", "mobil", "parking", "toll", "subway", "metro", "bus",
        "train", "amtrak", "transit", "car wash", "oil change", "auto repair"
    ],
    "Entertainment & Leisure": [
        "movie", "cinema", "theatre", "amc", "steam", "playstation", "xbox", "nintendo",
        "game", "concert", "ticket", "event", "bowling", "museum", "club", "party", "hobby"
    ],
    "Healthcare & Medical": [
        "hospital", "doctor", "clinic", "pharmacy", "medicine", "prescription", "dental",
        "dentist", "optometry", "glasses", "physician", "cvs", "walgreens", "therapy", "gym", "fitness"
    ],
    "Shopping": [
        "amazon", "ebay", "clothes", "apparel", "shoes", "nike", "adidas", "zara", "h&m",
        "electronics", "apple", "best buy", "mall", "store", "watch", "jewelry", "cosmetics", "sephora"
    ],
    "Subscriptions": [
        "netflix", "spotify", "hulu", "disney", "prime", "youtube premium", "apple music",
        "chatgpt", "openai", "github", "dropbox", "icloud", "subscription", "membership"
    ],
    "Travel & Vacations": [
        "flight", "airline", "hotel", "airbnb", "booking.com", "expedia", "resort", "vacation",
        "trip", "delta", "united", "american airlines", "luggage", "travel", "cruise"
    ],
    "Education": [
        "tuition", "course", "udemy", "coursera", "book", "university", "college", "school",
        "bootcamp", "training", "textbook", "udacity", "edx"
    ],
    "Salary & Wages": [
        "salary", "payroll", "paycheck", "wages", "direct deposit", "bonus", "employer", "stipend"
    ],
    "Freelance & Consulting": [
        "freelance", "consulting", "upwork", "fiverr", "client payment", "invoice payment", "contract"
    ],
    "Investments & Dividends": [
        "dividend", "stock", "etf", "crypto", "interest", "capital gain", "robinhood", "fidelity", "vanguard"
    ]
}


class ExpenseCategorizer:
    """
    Intelligent categorization using keyword token matching and optional LLM integration.
    """

    @classmethod
    def predict_category(cls, description, user_id=None):
        """
        Predicts category name and finds matching Category model object if user_id is provided.
        """
        if not description:
            return "Miscellaneous", None

        desc_clean = description.lower()

        # Check keyword matches
        best_cat_name = "Miscellaneous"
        highest_match = 0

        for cat_name, keywords in CATEGORY_KEYWORD_MAP.items():
            matches = 0
            for kw in keywords:
                # Whole-word regex match or substring for distinct tokens
                if re.search(r'\b' + re.escape(kw) + r'\b', desc_clean) or kw in desc_clean:
                    matches += 1
            if matches > highest_match:
                highest_match = matches
                best_cat_name = cat_name

        category_obj = None
        if user_id:
            # Look for matching Category in user's categories
            category_obj = Category.query.filter(
                Category.user_id == user_id,
                Category.category_name.ilike(f"%{best_cat_name}%")
            ).first()
            
            if not category_obj:
                # Try finding any category that matches any keyword in description
                user_cats = Category.query.filter_by(user_id=user_id).all()
                for c in user_cats:
                    if c.category_name.lower() in desc_clean or desc_clean in c.category_name.lower():
                        category_obj = c
                        best_cat_name = c.category_name
                        break

        return best_cat_name, category_obj

    @classmethod
    def parse_natural_language_transaction(cls, prompt_text, user_id=None):
        """
        Parses natural language transaction inputs:
        Examples:
        - "Spent 500 on Uber yesterday" -> amount: 500, type: expense, category: Transportation & Fuel, merchant: Uber
        - "Had dinner at KFC $650" -> amount: 650, type: expense, category: Food & Dining, merchant: KFC
        - "Received $3250 salary from Tech Corp today" -> amount: 3250, type: income, category: Salary & Wages
        """
        text = prompt_text.strip()

        # 1. Extract Amount ($500, 500.50, 650, etc.)
        amount = 0.0
        amt_match = re.search(r'(?:\$|₹|€|£)?\s*(\d+(?:,\d{3})*(?:\.\d{1,2})?)\s*(?:dollars|usd|rs|inr|eur)?', text, re.IGNORECASE)
        if amt_match:
            try:
                amt_str = amt_match.group(1).replace(',', '')
                amount = float(amt_str)
            except ValueError:
                amount = 0.0

        # 2. Determine Transaction Type (income vs expense)
        income_cues = ["received", "income", "salary", "earned", "got paid", "deposit", "bonus", "dividend"]
        is_income = any(cue in text.lower() for cue in income_cues)
        tx_type = "income" if is_income else "expense"

        # 3. Extract Date (yesterday, today, last monday, or standard YYYY-MM-DD)
        today = date.today()
        tx_date = today
        if "yesterday" in text.lower():
            tx_date = today - timedelta(days=1)
        elif "day before yesterday" in text.lower():
            tx_date = today - timedelta(days=2)
        else:
            # Check for explicit date like 2026-08-30 or 08/30/2026
            date_match = re.search(r'\b(\d{4}-\d{1,2}-\d{1,2})\b', text)
            if date_match:
                try:
                    tx_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                except ValueError:
                    pass

        # 4. Predict Category and clean merchant description
        cat_name, cat_obj = cls.predict_category(text, user_id=user_id)

        # 5. Extract cleaned description / merchant
        # Remove verbs and common noise
        cleaned_desc = re.sub(r'\b(spent|paid|bought|received|earned|yesterday|today|from|for|on|at|with|using|\$|₹|€)\b', '', text, flags=re.IGNORECASE)
        # Remove the numeric amount
        if amt_match:
            cleaned_desc = cleaned_desc.replace(amt_match.group(0), '')
        cleaned_desc = re.sub(r'\s+', ' ', cleaned_desc).strip().title()

        if not cleaned_desc or len(cleaned_desc) < 2:
            cleaned_desc = f"{cat_name} payment"

        return {
            'amount': amount,
            'transaction_type': tx_type,
            'category_name': cat_name,
            'category_id': cat_obj.id if cat_obj else None,
            'description': cleaned_desc,
            'transaction_date': tx_date.strftime('%Y-%m-%d'),
            'confidence': 0.92 if amount > 0 else 0.5
        }
