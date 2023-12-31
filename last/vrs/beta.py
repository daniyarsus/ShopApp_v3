from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import jwt
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware


# Database setup
DATABASE_URL = "sqlite:///home/king/PycharmProjects/ShopApp_v3/vrs/test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# User model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship("Shop")


class Shop(Base):
    __tablename__ = "shops"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)


# Dish model
class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship("Shop")



# Queue model
class QueueItem(Base):
    __tablename__ = "queue"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False)
    is_order_ready = Column(Boolean, default=False)
    user = relationship("User")
    shop = relationship("Shop")


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic models
class UserIn(BaseModel):
    username: str
    password: str


class Logout(BaseModel):
    access_token: str


class ShopCreate(BaseModel):
    name: str


class DishCreate(BaseModel):
    name: str


class QueueAdd(BaseModel):
    dish_id: int
    shop_id: int


class QueueReady(BaseModel):
    shop_id: int
    queue_id: int


class ShopMenuRequest(BaseModel):
    shop_id: int


# Pydantic model для обновления пароля
class UpdatePassword(BaseModel):
    old_password: str
    new_password: str


# Security and authentication
SECRET_KEY = "12345"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#import redis
#
## Настройки Redis
#REDIS_HOST = 'localhost'
#REDIS_PORT = 6379
#REDIS_DB = 0
#
## Подключение к Redis
#redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


# Helper functions
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    # Сохранение сессии в Redis
#    redis_client.setex(encoded_jwt, int(expires_delta.total_seconds() if expires_delta else 900), str(data['sub']))

    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    session = SessionLocal()
    user = session.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    return user


# Функция для получения всех пользователей из базы данных
def get_all_users():
    session = SessionLocal()
    users = session.query(User).all()
    session.close()
    return users

# FastAPI app
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# User endpoints
@app.post("/register")
async def register(user_in: UserIn):
    session = SessionLocal()

    # Проверка существования пользователя с указанным именем
    existing_user = session.query(User).filter(User.username == user_in.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User is registered")

    # Создание нового пользователя
    user = User(username=user_in.username, password=user_in.password)
    session.add(user)
    session.commit()

    return {"username": user.username}


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    session = SessionLocal()
    user = session.query(User).filter(User.username == form_data.username).first()
    if not user or user.password != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


#@app.post("/logout")
#async def logout(logout: Logout, current_user: User = Depends(get_current_user)):
#    access_token = logout.access_token
#    redis_client.delete(access_token)  # Удаление сессии из Redis
#    response = Response()
#    response.delete_cookie("access_token")
#    return {"message": "Logged out successfully"}


@app.get("/user/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@app.put("/user/change_password")
async def change_password(new_password: UpdatePassword, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Проверяем старый пароль
    if current_user.password != new_password.old_password:
        raise HTTPException(status_code=400, detail="Old password is incorrect")

    # Асинхронная функция для изменения пароля пользователя
    async def update_password(user_id: int, password: str):
        user_db = session.query(User).filter(User.id == user_id).first()
        if not user_db:
            raise HTTPException(status_code=404, detail="User not found")
        user_db.password = password
        session.commit()

    # Изменяем пароль текущего пользователя
    await update_password(current_user.id, new_password.new_password)

    session.close()
    return {"message": "Password updated successfully"}


# Shop endpoints
@app.post("/shop/create")
async def create_shop(shop_create: ShopCreate, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Проверка, является ли текущий пользователь авторизованным
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    existing_shop = session.query(Shop).filter(Shop.name == shop_create.name).first()
    if existing_shop:
        raise HTTPException(status_code=400, detail="Shop already exists")

    shop = Shop(name=shop_create.name)
    session.add(shop)
    session.commit()
    return {"shop_id": shop.id, "name": shop.name}


@app.post("/shop/dish/create")
async def create_dish(dish_create: DishCreate, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Ensure the current user has a shop associated
    if not current_user.shop_id:
        raise HTTPException(status_code=403, detail="No shop associated with the current user")

    # Create a new dish with the current user's shop_id
    dish = Dish(name=dish_create.name, shop_id=current_user.shop_id)
    session.add(dish)
    session.commit()
    return {"dish_id": dish.id, "name": dish.name, "shop_id": dish.shop_id}


@app.post("/shop/menu")
async def get_menu(shop_menu_request: ShopMenuRequest):
    session = SessionLocal()

    # Получаем все блюда для конкретного магазина
    menu_items = session.query(Dish).filter(Dish.shop_id == shop_menu_request.shop_id).all()

    # Закрываем сессию
    session.close()

    # Формируем результат
    result = [{"dish_id": item.id, "name": item.name, "shop_id": item.shop_id} for item in menu_items]

    return result


# Эндпоинт для добавления в очередь
@app.post("/shop/queue/add")
async def add_to_queue(queue_add: QueueAdd, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Проверяем, существует ли уже запись в очереди для текущего пользователя и магазина
    existing_queue_item = session.query(QueueItem).filter(
        QueueItem.user_id == current_user.id,
        QueueItem.is_order_ready == False  # Проверка, что заказ еще не готов
    ).first()

    if existing_queue_item:
        session.close()
        raise HTTPException(status_code=400, detail="User is already in the queue")

    # Проверяем, существует ли блюдо с указанным ID
    dish = session.query(Dish).filter(Dish.id == queue_add.dish_id).first()
    if not dish:
        session.close()
        raise HTTPException(status_code=404, detail="Dish not found")

    # Создаем запись в очереди
    queue_item = QueueItem(user_id=current_user.id, shop_id=dish.shop_id)
    session.add(queue_item)
    session.commit()
    session.refresh(queue_item)

    # Закрываем сессию
    session.close()

    return {"queue_id": queue_item.id, "message": "You've been added to the queue"}


@app.post("/shop/queue/ready")
async def order_ready(queue_ready: QueueReady, current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Проверяем, привязан ли текущий пользователь к выбранному магазину
    if current_user.shop_id != queue_ready.shop_id:
        raise HTTPException(status_code=403, detail="You are not allowed to mark orders as ready for this shop")

    # Получаем запись в очереди
    queue_item = session.query(QueueItem).filter(
        QueueItem.id == queue_ready.queue_id,
        QueueItem.shop_id == queue_ready.shop_id,
        QueueItem.is_order_ready == False  # Проверка, что заказ еще не готов
    ).first()

    if not queue_item:
        session.close()
        raise HTTPException(status_code=404, detail="Queue item not found")

    # Помечаем заказ как готовый
    queue_item.is_order_ready = True
    session.commit()

    # Закрываем сессию
    session.close()

    return {"queue_id": queue_ready.queue_id, "message": "Order is ready for pickup"}


# Измененный эндпоинт для проверки статуса очереди у магазина
@app.get("/shop/queue/status")
async def check_shop_queue_status(current_user: User = Depends(get_current_user)):
    session = SessionLocal()
    shop = session.query(Shop).filter(Shop.id == current_user.shop_id).first()

    if not shop:
        raise HTTPException(status_code=404, detail="Shop not found")

    # Получаем все записи в очереди для данного магазина с информацией о пользователе,
    # отсортированные в обратном порядке
    shop_queue_status = session.query(QueueItem, User).join(User).filter(
        QueueItem.shop_id == shop.id
    ).order_by(QueueItem.id.desc()).all()

    # Закрываем сессию
    session.close()

    # Формируем результат, включая username пользователя в очереди
    result = [{"queue_id": queue_item.id, "is_order_ready": queue_item.is_order_ready, "username": user.username} for
              queue_item, user in shop_queue_status]

    return result


@app.get("/shop/queue/my_queue_status")
async def my_queue_status(current_user: User = Depends(get_current_user)):
    session = SessionLocal()

    # Получаем все записи в очереди для текущего пользователя, отсортированные в обратном порядке
    user_queue_status = session.query(QueueItem).filter(QueueItem.user_id == current_user.id).order_by(
        QueueItem.id.desc()).first()

    # Закрываем сессию
    session.close()

    return user_queue_status


# Эндпоинт для вывода всех данных из таблицы Users
@app.get("/users_all")
async def read_all_users():
    users = get_all_users()
    return users

