from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📦 Order"), KeyboardButton(text="💸 Withdraw")],
            [KeyboardButton(text="💰 Balance"), KeyboardButton(text="👥 Referral")],
            [KeyboardButton(text="👤 Profile")],
        ],
        resize_keyboard=True
    )

def start_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 New Registration", callback_data="register")],
            [InlineKeyboardButton(text="🔐 Login", callback_data="login")],
        ]
    )
