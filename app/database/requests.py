import os

from app.database.models import async_session, User, Announ
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError


async def set_user(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        
        if not user:
            session.add(User(tg_id=tg_id))
            await session.commit()
        

async def set_annon(name, description, img_id, contacts, user_tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == user_tg_id))
        
        session.add(Announ(name=name, description=description, contacts=contacts, img_id=img_id, owner_id=user.id))
        await session.commit()


async def get_annons():
    async with async_session() as session:
        return await session.scalars(select(Announ))

async def get_user_annons(tg_id):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        return await session.scalars(select(Announ).where(Announ.owner_id == user.id))

async def delete_annons(id):
    async with async_session() as session:
        announ = await session.scalar(select(Announ).where(Announ.id == id))
        if os.path.exists(f'downloads/{announ.img_id}.jpg'):
            os.remove(f'downloads/{announ.img_id}.jpg')
        await session.execute(delete(Announ).where(Announ.id == id))
        await session.commit()
        return announ

# async def get_categories():
#     async with async_session() as session:
#         return await session.scalars(select(Category))


# async def get_items_by_category(category_id):
#     async with async_session() as session:
#         return await session.scalars(select(Item).where(Item.category == category_id))


# async def get_items(item_id):
#     async with async_session() as session:
#         return await session.scalar(select(Item).where(Item.id == item_id))