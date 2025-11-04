import os
import asyncio
from typing import List, Optional, Tuple
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.database.requests import set_user, set_annon, get_annons, get_user_annons, delete_annons
import app.keyboards as kb


router = Router()

INV_SYMBOLS = {'<', '>'}

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Hello!', reply_markup=kb.main_kb)
    await set_user(message.from_user.id)


class AddAd(StatesGroup):
    name = State()
    description = State()
    img_id = State()
    contacts = State()


@router.message(F.text == '📝 Создать объявление')
async def create_ad(message: Message, state: StatesGroup):
    await message.answer('Введите название объявления')
    
    await state.set_state(AddAd.name)

@router.message(F.text, AddAd.name)
async def get_name(message: Message, state: FSMContext):
    if INV_SYMBOLS.intersection(message.text):
        await message.answer('Название не должно содержать специальных символов')
        await create_ad(message, state)
        return False
    await state.update_data(name=message.text)
    
    await message.answer('Введите описание объявления')
    await state.set_state(AddAd.description)

@router.message(F.text, AddAd.description)
async def get_description(message: Message, state: FSMContext):
    if INV_SYMBOLS.intersection(message.text):
        await message.answer('Описание не должно содержать специальных символов')
        await get_name(message, state)
        return False
    await state.update_data(description=message.text)
    
    await message.answer('Отправьте фото объявления')
    await state.set_state(AddAd.img_id)
    

@router.message(F.photo, AddAd.img_id)
async def get_img(message: Message, state: FSMContext, bot: Bot):
    photo = message.photo[-1]
    
    os.makedirs('downloads', exist_ok=True)
    
    file = await bot.get_file(photo.file_id)
    file_path = f'downloads/{photo.file_id}.jpg'
    await bot.download_file(file.file_path, file_path)
    
    await state.update_data(img_id=photo.file_id)
    
    await message.answer('Введите контакты')
    await state.set_state(AddAd.contacts)

@router.message(F.text, AddAd.contacts)
async def get_contacts(message: Message, state: FSMContext):
    await state.update_data(contacts=message.text)
    
    data = await state.get_data()
    await set_annon(data['name'], data['description'], data['img_id'], data['contacts'], message.from_user.id)
    await message.answer('Объявление создано!', reply_markup=kb.main_kb)
    await state.clear()


@router.message(F.text == '📃 Все объявления')
async def get_all_ad(message: Message):
    await show_annons_menu(message)


@router.message(F.text == '📰 Мои объявления')
async def get_user_ad(message: Message):
    await show_my_annons(message)

# @router.message(F.photo)
# async def handle_photo(message: Message, bot: Bot):
#     photo = message.photo[-1]
    
#     # Создаем папку для загрузок
#     os.makedirs("downloads", exist_ok=True)
    
#     # Скачиваем фото
#     file = await bot.get_file(photo.file_id)
#     file_path = f"downloads/{photo.file_id}.jpg"
#     await bot.download_file(file.file_path, file_path)
    
    
#     # Сохраняем в базу данных
#     # db.save_photo(
#     #     user_id=user_id,
#     #     file_id=photo.file_id,
#     #     file_path=file_path,
#     #     file_size=photo.file_size,
#     #     width=photo.width,
#     #     height=photo.height,
#     #     caption=message.caption
#     # )
    
#     await message.answer(
#         f"✅ Фото сохранено!\n"
#         f"📊 Размер: {photo.width}x{photo.height}\n"
#         f"💾 Вес: {photo.file_size} байт\n"
#         f"📝 Подпись: {message.caption or 'нет'}"
#     )

class Pagination:
    def __init__(self, data: List, page_size: int = 1):
        self.data = data
        self.page_size = page_size
        self.total_pages = (len(data) + page_size - 1) // page_size
        self.current_page = 1
    
    def get_page(self, page: int) -> List:
        if not self.data:
            return []
        start_idx = (page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.data[start_idx:end_idx]
    
    def get_page_info(self) -> Tuple[int, int]:
        return self.current_page, self.total_pages

# Хранилище пагинации по пользователям
user_pagination = {}

async def show_annons_menu(message: Message):
    # Получаем объявления
    annons_data = (await get_annons()).all()  # Ваша функция
    
    if not annons_data:
        await message.answer("Объявления не найдены")
        return
    
    # Создаем пагинацию для пользователя
    pagination = Pagination(annons_data)
    user_pagination[message.from_user.id] = pagination
    
    # Показываем первую страницу
    await show_annons_page(message, pagination)


async def show_annons_page(message: Message, pagination: Pagination, edit: bool = False):
    current_annons = pagination.get_page(pagination.current_page)
    
    if not current_annons:
        await message.answer("Нет данных для отображения")
        return
    
    annon = current_annons[0]  # Берем первое объявление на странице
    
    # Формируем текст объявления
    text = (
        f"<b>{annon.name}</b>\n\n"
        f"{annon.description}\n"
        f"<b>Контакты:</b>\n{annon.contacts}\n\n"
        f"Страница {pagination.current_page} из {pagination.total_pages}"
    )
    
    # Создаем клавиатуру с пагинацией
    keyboard = InlineKeyboardBuilder()
    
    if pagination.current_page > 1:
        keyboard.button(text="⬅️ Назад", callback_data=f"annons_prev_{pagination.current_page}")
    
    if pagination.current_page < pagination.total_pages:
        keyboard.button(text="Вперед ➡️", callback_data=f"annons_next_{pagination.current_page}")
    
    
    keyboard.adjust(2, 1)
    
    # Получаем файл картинки (предполагаем, что img_id - это file_id)
    if annon.img_id:
        if edit:
            # Редактируем существующее сообщение
            media = InputMediaPhoto(
                media=annon.img_id,
                caption=text,
                parse_mode="HTML"
            )
            await message.edit_media(media, reply_markup=keyboard.as_markup())
        else:
            # Отправляем новое сообщение
            await message.answer_photo(
                photo=annon.img_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )
    else:
        if edit:
            await message.edit_text(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )
        else:
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )

@router.callback_query(F.data.startswith("annons_"))
async def handle_annons_pagination(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in user_pagination:
        await callback.answer("Сессия истекла, вызовите /annons снова")
        return
    
    pagination = user_pagination[user_id]
    action = callback.data.split("_")[1]
    
    if action == "prev" and pagination.current_page > 1:
        pagination.current_page -= 1
    elif action == "next" and pagination.current_page < pagination.total_pages:
        pagination.current_page += 1
    
    await show_annons_page(callback.message, pagination, edit=True)
    await callback.answer()

# Альтернативная версия с более простой навигацией
@router.callback_query(F.data == "annons_menu")
async def show_annons_menu_callback(callback: CallbackQuery):
    await callback.message.delete()
    await show_annons_menu(callback.message)

# Функция для очистки старых сессий (опционально)
async def cleanup_old_sessions():
    """Очистка старых сессий пагинации"""
    current_time = asyncio.get_event_loop().time()
    # Можно добавить логику очистки по времени
    # Например, удалять сессии старше 1 часа

# Если нужно использовать глобальную пагинацию вместо user_pagination
class AnnonsManager:
    def __init__(self):
        self.sessions = {}
    
    async def get_user_session(self, user_id: int):
        if user_id not in self.sessions:
            annons_data = await get_annons()
            self.sessions[user_id] = Pagination(annons_data)
        return self.sessions[user_id]
    
    def cleanup_session(self, user_id: int):
        if user_id in self.sessions:
            del self.sessions[user_id]

# Использование менеджера
annons_manager = AnnonsManager()

@router.message(Command("annons2"))
async def show_annons_menu_v2(message: Message):
    pagination = await annons_manager.get_user_session(message.from_user.id)
    await show_annons_page(message, pagination)

class UserAnnonsPagination:
    def __init__(self, data: List, page_size: int = 1):
        self.data = data
        self.page_size = page_size
        self.total_pages = (len(data) + page_size - 1) // page_size
        self.current_page = 1
    
    def get_page(self, page: int) -> List:
        if not self.data:
            return []
        start_idx = (page - 1) * self.page_size
        end_idx = start_idx + self.page_size
        return self.data[start_idx:end_idx]
    
    def get_current_annons(self) -> Optional:
        """Получить текущее объявление"""
        current = self.get_page(self.current_page)
        return current[0] if current else None
    
    def remove_annons(self, annons_id: int):
        """Удалить объявление из списка"""
        self.data = [item for item in self.data if item.id != annons_id]
        self.total_pages = (len(self.data) + self.page_size - 1) // self.page_size
        # Корректируем текущую страницу, если нужно
        if self.current_page > self.total_pages and self.total_pages > 0:
            self.current_page = self.total_pages

# Хранилище пагинации по пользователям
user_annons_sessions = {}

@router.message(Command("my_annons"))
async def show_my_annons(message: Message):
    """Показать объявления пользователя"""
    user_id = message.from_user.id
    
    # Получаем объявления пользователя
    annons_data = (await get_user_annons(user_id)).all()  # Ваша функция
    
    if not annons_data:
        await message.answer("У вас пока нет объявлений")
        return
    
    # Создаем пагинацию для пользователя
    pagination = UserAnnonsPagination(annons_data)
    user_annons_sessions[user_id] = pagination
    
    # Показываем первую страницу
    await show_user_annons_page(message, pagination)

async def show_user_annons_page(message: Message, pagination: UserAnnonsPagination, edit: bool = False):
    """Показать страницу с объявлениями пользователя"""
    annon = pagination.get_current_annons()
    
    if not annon:
        text = "У вас пока нет объявлений"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✏️ Создать объявление", callback_data="create_annons")
        keyboard.adjust(1)
        
        if edit:
            await message.edit_text(text, reply_markup=keyboard.as_markup())
        else:
            await message.answer(text, reply_markup=keyboard.as_markup())
        return
    
    # Формируем текст объявления
    text = (
        f"<b>📢 Ваше объявление</b>\n\n"
        f"<b>Название:</b> {annon.name}\n\n"
        f"{annon.description}\n"
        f"<b>Контакты:</b> {annon.contacts}\n\n"
        f"<i>Страница {pagination.current_page} из {pagination.total_pages}</i>"
    )
    
    # Создаем клавиатуру с пагинацией и действиями
    keyboard = InlineKeyboardBuilder()
    
    # Кнопки навигации
    if pagination.current_page > 1:
        keyboard.button(text="⬅️ Назад", callback_data=f"my_annons_prev_{pagination.current_page}")
    
    if pagination.current_page < pagination.total_pages:
        keyboard.button(text="Вперед ➡️", callback_data=f"my_annons_next_{pagination.current_page}")
    
    # Кнопки действий
    keyboard.button(text="🗑️ Удалить", callback_data=f"delete_annons_{annon.id}")
    
    # Распределяем кнопки по рядам
    if pagination.total_pages > 1:
        keyboard.adjust(2, 2, 1)
    else:
        keyboard.adjust(2, 1)
    
    # Отправляем/редактируем сообщение с фото
    if annon.img_id:
        if edit:
            media = InputMediaPhoto(
                media=annon.img_id,
                caption=text,
                parse_mode="HTML"
            )
            await message.edit_media(media, reply_markup=keyboard.as_markup())
        else:
            await message.answer_photo(
                photo=annon.img_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )
    else:
        if edit:
            await message.edit_text(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )
        else:
            await message.answer(
                text=text,
                parse_mode="HTML",
                reply_markup=keyboard.as_markup()
            )

@router.callback_query(F.data.startswith("my_annons_"))
async def handle_my_annons_pagination(callback: CallbackQuery):
    """Обработка пагинации объявлений пользователя"""
    user_id = callback.from_user.id
    
    if user_id not in user_annons_sessions:
        await callback.answer("Сессия истекла")
        return
    
    pagination = user_annons_sessions[user_id]
    data_parts = callback.data.split("_")
    action = data_parts[2]
    
    if action == "prev" and pagination.current_page > 1:
        pagination.current_page -= 1
    elif action == "next" and pagination.current_page < pagination.total_pages:
        pagination.current_page += 1
    elif action == "close":
        await callback.message.delete()
        if user_id in user_annons_sessions:
            del user_annons_sessions[user_id]
        return
    
    await show_user_annons_page(callback.message, pagination, edit=True)
    await callback.answer()

@router.callback_query(F.data.startswith("delete_annons_"))
async def handle_delete_annons(callback: CallbackQuery):
    """Обработка удаления объявления"""
    user_id = callback.from_user.id
    annons_id = int(callback.data.split("_")[2])
    
    if user_id not in user_annons_sessions:
        await callback.answer("Сессия истекла")
        return
    
    pagination = user_annons_sessions[user_id]
    
    # Удаляем объявление из базы данных
    success = await delete_annons(annons_id)  # Ваша функция удаления
    
    if success:
        # Удаляем из локального списка
        pagination.remove_annons(annons_id)
        await callback.answer("Объявление удалено")
        
        # Если список пуст после удаления
        if not pagination.data:
            await callback.message.delete()
            del user_annons_sessions[user_id]
            await callback.message.answer("Все объявления удалены")
            return
        
        # Показываем обновленный список
        await show_user_annons_page(callback.message, pagination, edit=True)
    else:
        await callback.answer("Ошибка при удалении объявления")


async def cleanup_sessions():
    """Очистка всех сессий"""
    user_annons_sessions.clear()