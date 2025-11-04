from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.database.requests import get_annons


main_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='📃 Все объявления')], 
                                        [KeyboardButton(text='📝 Создать объявление')],
                                        [KeyboardButton(text='📰 Мои объявления')],
                                        ], resize_keyboard=True, one_time_keyboard=True)


async def anonns():
    all_annons = await get_annons()
    keyboard = InlineKeyboardBuilder()
    
    for annon in all_annons:
        keyboard.row(InlineKeyboardButton())

