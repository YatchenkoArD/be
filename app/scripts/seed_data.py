# app/scripts/seed_data.py
import asyncio
import json
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.models.models import (
    Salon, Master, User, Service, Promotion, UserRole, Base,
    SalonMember, SalonRole, OWNER_DEFAULT_PERMISSIONS,
    Booking, BookingStatus, Review,
    SalonLoyaltySettings, LoyaltyOffer, ClientLoyalty, LoyaltyStatusSource,
    InventoryItem, MasterPayrollSettings,
)
from app.core.config import settings
from app.core.security import get_password_hash

# График работы: слоты записи считаются от него (schedule_utils) — без графика
# ни один салон не покажет ни одного слота.
WORK_WEEK = json.dumps({
    "mon": "10:00-21:00", "tue": "10:00-21:00", "wed": "10:00-21:00",
    "thu": "10:00-21:00", "fri": "10:00-21:00", "sat": "11:00-19:00",
    "sun": "выходной",
})
WORK_DAILY = json.dumps({
    d: "10:00-20:00" for d in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
})

# Единый dev-пароль для всех сидовых пользователей (Argon2id). Только для локалки.
DEV_PASSWORD = "Seedpass1"

async def seed_database():
    engine = create_async_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Создаём таблицы (если их ещё нет)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Проверяем, есть ли уже салоны в базе
        existing_salons = await session.execute(select(func.count(Salon.id)))
        salon_count = existing_salons.scalar()
        
        if salon_count > 0:
            print(f"✅ База уже содержит {salon_count} салонов. Seed не требуется.")
            return
        
        print("🔄 База пуста. Заполняем тестовыми данными...")
        
        # ========== САЛОНЫ ==========
        s1 = Salon(name="Брутальный", description="Мужские стрижки, борода, уход", address="Москва, ул. Тверская, 15", latitude=55.761859, longitude=37.606138, phone="+79991234567", rating=0.0, reviews_count=0, timezone="Asia/Novosibirsk", working_hours=WORK_WEEK)
        s2 = Salon(name="Classic", description="Классические мужские стрижки", address="Санкт-Петербург, Невский пр., 22", latitude=59.934280, longitude=30.335099, phone="+78121234567", rating=0.0, reviews_count=89, timezone="Asia/Novosibirsk", working_hours=WORK_DAILY)
        s3 = Salon(name="Имидж", description="Женские и мужские стрижки, окрашивание", address="Москва, пр. Мира, 45", latitude=55.779438, longitude=37.636928, phone="+74959876543", rating=0.0, reviews_count=234, timezone="Asia/Novosibirsk", working_hours=WORK_WEEK)
        s4 = Salon(name="Гламур", description="Маникюр, педикюр, наращивание", address="Санкт-Петербург, Большой пр. П.С., 10", latitude=59.962264, longitude=30.308452, phone="+78123334455", rating=0.0, reviews_count=312, timezone="Asia/Novosibirsk", working_hours=WORK_DAILY)
        s5 = Salon(name="Элегант", description="Стрижки, укладки, уход за волосами", address="Казань, ул. Баумана, 33", latitude=55.792752, longitude=49.121467, phone="+78432987654", rating=0.0, reviews_count=178, timezone="Asia/Novosibirsk", working_hours=WORK_WEEK)
        session.add_all([s1, s2, s3, s4, s5])
        await session.flush()
        
        # ========== МАСТЕРА ==========
        # Брутальный
        u1 = User(phone="+79991112233", full_name="Александр Петров", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u1)
        await session.flush()
        m1 = Master(user_id=u1.id, salon_id=s1.id, specialization="барбер-стилист", experience_years=5, rating=0.0)
        session.add(m1)
        await session.flush()
        session.add_all([Service(master_id=m1.id, name="Стрижка машинкой", price=1500, duration_minutes=30), Service(master_id=m1.id, name="Стрижка + борода", price=2400, duration_minutes=60), Service(master_id=m1.id, name="Моделирование бороды", price=1200, duration_minutes=30)])
        
        u2 = User(phone="+79992223344", full_name="Дмитрий Волков", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u2)
        await session.flush()
        m2 = Master(user_id=u2.id, salon_id=s1.id, specialization="барбер-колорист", experience_years=3, rating=0.0)
        session.add(m2)
        await session.flush()
        session.add_all([Service(master_id=m2.id, name="Стрижка ножницами", price=2000, duration_minutes=45), Service(master_id=m2.id, name="Камуфляж седины", price=1800, duration_minutes=40)])
        
        # Classic
        u3 = User(phone="+78121112233", full_name="Сергей Козлов", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u3)
        await session.flush()
        m3 = Master(user_id=u3.id, salon_id=s2.id, specialization="стилист-парикмахер", experience_years=7, rating=0.0)
        session.add(m3)
        await session.flush()
        session.add_all([Service(master_id=m3.id, name="Классическая стрижка", price=1800, duration_minutes=40), Service(master_id=m3.id, name="Укладка", price=1200, duration_minutes=30), Service(master_id=m3.id, name="Спа-уход", price=2500, duration_minutes=60)])
        
        # Имидж
        u4 = User(phone="+74951113344", full_name="Елена Смирнова", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u4)
        await session.flush()
        m4 = Master(user_id=u4.id, salon_id=s3.id, specialization="стилист-колорист", experience_years=8, rating=0.0)
        session.add(m4)
        await session.flush()
        session.add_all([Service(master_id=m4.id, name="Окрашивание", price=4500, duration_minutes=120), Service(master_id=m4.id, name="Стрижка женская", price=3000, duration_minutes=60), Service(master_id=m4.id, name="Тонирование", price=2800, duration_minutes=90)])
        
        # Гламур
        u5 = User(phone="+78124445566", full_name="Ольга Иванова", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u5)
        await session.flush()
        m5 = Master(user_id=u5.id, salon_id=s4.id, specialization="мастер маникюра", experience_years=6, rating=0.0)
        session.add(m5)
        await session.flush()
        session.add_all([Service(master_id=m5.id, name="Маникюр классический", price=1800, duration_minutes=60), Service(master_id=m5.id, name="Педикюр", price=2500, duration_minutes=90), Service(master_id=m5.id, name="Наращивание ногтей", price=3500, duration_minutes=120)])
        
        # Элегант
        u6 = User(phone="+78431112233", full_name="Марина Попова", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MASTER, is_active=True)
        session.add(u6)
        await session.flush()
        m6 = Master(user_id=u6.id, salon_id=s5.id, specialization="стилист-визажист", experience_years=4, rating=0.0)
        session.add(m6)
        await session.flush()
        session.add_all([Service(master_id=m6.id, name="Стрижка + укладка", price=2500, duration_minutes=60), Service(master_id=m6.id, name="Окрашивание бровей", price=1200, duration_minutes=30), Service(master_id=m6.id, name="Ламинирование ресниц", price=2000, duration_minutes=60)])
        
        # ========== АКЦИИ ==========
        promos = [
            (s1.id, "Первый визит −20%", "Скидка 20% на все услуги для новых клиентов", "Новичкам"),
            (s1.id, "Комбо стрижка + борода", "Стрижка и моделирование бороды за 2200₽ вместо 2400₽", "Выгода"),
            (s2.id, "Приведи друга", "Получите скидку 500₽ за каждого приведённого друга", "Друзьям"),
            (s3.id, "Окрашивание + укладка", "При окрашивании — укладка в подарок", "Подарок"),
            (s3.id, "Счастливые часы", "Скидка 15% на все услуги с 09:00 до 12:00", "−15%"),
            (s4.id, "Маникюр + педикюр", "Комбо со скидкой 10% при заказе двух услуг", "−10%"),
            (s4.id, "День рождения", "Скидка 25% на любые услуги в день рождения и 3 дня после", "🎂"),
            (s5.id, "Брови + ресницы", "Коррекция и окрашивание бровей + ламинирование ресниц за 2500₽", "Комбо"),
            (s5.id, "Студентам −15%", "Скидка 15% на стрижки по студенческому", "Студентам"),
        ]
        for sid, title, desc, tag in promos:
            session.add(Promotion(salon_id=sid, title=title, description=desc, tag=tag))
        
        # ========== ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ ==========
        # Пароль у всех — DEV_PASSWORD ("Seedpass1"), хеш Argon2id. Только для dev.
        test_users = [
            User(phone="+79990000001", full_name="Анна Клиент", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.CLIENT, is_active=True),
            User(phone="+79990000002", full_name="Игорь Владелец", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.BUSINESS, is_active=True),
            User(phone="+79990000003", full_name="Мария Модель", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.MODEL, is_active=True),
        ]
        
        for tu in test_users:
            existing = await session.execute(select(User).where(User.phone == tu.phone))
            if not existing.scalar_one_or_none():
                session.add(tu)
        
        # Привязываем владельца к первому салону
        owner = await session.execute(select(User).where(User.phone == "+79990000002"))
        owner = owner.scalar_one_or_none()
        if owner and not s1.creator_id:
            s1.creator_id = owner.id
            await session.flush()
            existing_membership = await session.execute(
                select(SalonMember).where(SalonMember.salon_id == s1.id, SalonMember.user_id == owner.id)
            )
            if not existing_membership.scalar_one_or_none():
                session.add(SalonMember(
                    salon_id=s1.id, user_id=owner.id, role=SalonRole.OWNER,
                    is_creator=True, permissions=dict(OWNER_DEFAULT_PERMISSIONS), is_active=True,
                ))

        # ========== ВЛАДЕЛЬЦЫ ОСТАЛЬНЫХ САЛОНОВ + СОТРУДНИК С ОГРАНИЧЕННЫМИ ПРАВАМИ ==========
        # Игорь (+...0002) владеет s1 (выше) и s2 — кейс «несколько салонов у одного
        # владельца». Светлана — владелица s3. Тимур — админ в s1 с урезанными
        # правами (только склад и записи) — для демонстрации матрицы прав.
        owner2 = User(phone="+79990000004", full_name="Светлана Хозяйка", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.BUSINESS, is_active=True)
        staff1 = User(phone="+79990000005", full_name="Тимур Администратор", hashed_password=get_password_hash(DEV_PASSWORD), role=UserRole.CLIENT, is_active=True)
        session.add_all([owner2, staff1])
        await session.flush()

        if owner:
            s2.creator_id = owner.id
            session.add(SalonMember(salon_id=s2.id, user_id=owner.id, role=SalonRole.OWNER,
                                    is_creator=True, permissions=dict(OWNER_DEFAULT_PERMISSIONS), is_active=True))
        s3.creator_id = owner2.id
        session.add(SalonMember(salon_id=s3.id, user_id=owner2.id, role=SalonRole.OWNER,
                                is_creator=True, permissions=dict(OWNER_DEFAULT_PERMISSIONS), is_active=True))
        session.add(SalonMember(salon_id=s1.id, user_id=staff1.id, role=SalonRole.ADMIN,
                                is_creator=False, is_active=True,
                                permissions={"manage_inventory": True, "manage_bookings": True}))

        # ========== ЗАПИСИ (в разных статусах, в рабочие часы 10–21) ==========
        client_user = await session.execute(select(User).where(User.phone == "+79990000001"))
        client_user = client_user.scalar_one()
        svc_m1 = (await session.execute(select(Service).where(Service.master_id == m1.id))).scalars().first()
        svc_m3 = (await session.execute(select(Service).where(Service.master_id == m3.id))).scalars().first()

        def _at(day_shift: int, hour: int) -> datetime:
            return (datetime.now() + timedelta(days=day_shift)).replace(hour=hour, minute=0, second=0, microsecond=0)

        bookings = [
            # прошедшая выполненная — видна в истории и в карточке клиента CRM
            Booking(client_id=client_user.id, master_id=m1.id, service_id=svc_m1.id,
                    start_time=_at(-5, 12), end_time=_at(-5, 13),
                    status=BookingStatus.COMPLETED, final_price=svc_m1.price),
            # будущая подтверждённая — завтра
            Booking(client_id=client_user.id, master_id=m1.id, service_id=svc_m1.id,
                    start_time=_at(1, 14), end_time=_at(1, 15),
                    status=BookingStatus.CONFIRMED, final_price=svc_m1.price),
            # будущая отменённая — виден статус в «Моих записях»
            Booking(client_id=client_user.id, master_id=m3.id, service_id=svc_m3.id,
                    start_time=_at(2, 16), end_time=_at(2, 17),
                    status=BookingStatus.CANCELLED, final_price=svc_m3.price),
        ]
        session.add_all(bookings)

        # ========== ОТЗЫВЫ ==========
        session.add_all([
            Review(client_id=client_user.id, master_id=m1.id, salon_id=s1.id, rating=5,
                   comment="Отличная стрижка, мастер топ!"),
            Review(client_id=client_user.id, master_id=m3.id, salon_id=s2.id, rating=4,
                   comment="Хорошо, но пришлось подождать 10 минут."),
        ])
        m1.rating = 5.0
        s1.rating = 5.0
        s1.reviews_count = 1
        m3.rating = 4.0

        # ========== ЛОЯЛЬНОСТЬ (салон Брутальный) ==========
        session.add(SalonLoyaltySettings(salon_id=s1.id, regular_client_discount_percent=5,
                                         regular_client_visits_threshold=3, bonus_accrual_percent=5.0))
        session.add(LoyaltyOffer(salon_id=s1.id, title="День рождения", discount_percent=15,
                                 promo_code="BDAY15", is_active=True))
        session.add(ClientLoyalty(salon_id=s1.id, client_id=client_user.id,
                                  is_regular_client=True, regular_client_source=LoyaltyStatusSource.MANUAL,
                                  bonus_points=150))

        # ========== СКЛАД И ЗАРПЛАТА (мастер Александр в Брутальном) ==========
        session.add_all([
            InventoryItem(master_id=m1.id, name="Шампунь профессиональный", unit="мл",
                          quantity=1500.0, cost_per_unit=2, min_quantity=300.0),
            InventoryItem(master_id=m1.id, name="Воск для укладки", unit="г",
                          quantity=200.0, cost_per_unit=8, min_quantity=50.0),
            InventoryItem(master_id=m1.id, name="Лезвия для бритвы", unit="шт",
                          quantity=18.0, cost_per_unit=45, min_quantity=20.0),  # ниже минимума — видна плашка
        ])
        session.add(MasterPayrollSettings(master_id=m1.id, base_salary=40000, commission_percent=30.0))

        await session.commit()
        print("✅ База заполнена: 5 салонов (график работы задан — слоты записи работают), "
              "6 мастеров, 17 услуг, 9 акций, владельцы+сотрудник, записи в 3 статусах, "
              "отзывы, лояльность, склад, зарплата!")

if __name__ == "__main__":
    asyncio.run(seed_database())