from sqlalchemy.orm import Session

import models
import schemas


def get_all_messages(db: Session):
    return db.query(models.Message).order_by(models.Message.create_time.asc()).all()

def get_message(db: Session, msg_id: int):
    return db.query(models.Message).filter(models.Message.id == msg_id).first()

def get_unhandled_message(db: Session, msg: schemas.MessageCreate):
    return db.query(models.Message).filter(models.Message.source == msg.source).filter(models.Message.content == msg.content).filter(models.Message.is_fulfilled == False).first()

# def get_user_by_email(db: Session, email: str):
#     return db.query(models.User).filter(models.User.email == email).first()


# def get_users(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.User).offset(skip).limit(limit).all()


def create_message(db: Session, message: schemas.MessageCreate):
    db_msg = models.Message(**message.dict())
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)
    return db_msg

def update_message(db: Session, model_msg: models.Message):
    db.add(model_msg)
    db.commit()
    db.refresh(model_msg)
    return model_msg

def get_or_create_message(db: Session, msg: schemas.MessageCreate):
    message = get_message(db, msg.id)
    if message:
        return message
    return create_message(db, msg)

# def get_unhandled_or_create_new_message(db: Session, msg: schemas.MessageCreate):
#     message = get_unhandled_message(db, msg)
#     if message:
#         return message
#     return create_message(db, msg)

# def get_items(db: Session, skip: int = 0, limit: int = 100):
#     return db.query(models.Item).offset(skip).limit(limit).all()


# def create_user_item(db: Session, item: schemas.ItemCreate, user_id: int):
#     db_item = models.Item(**item.dict(), owner_id=user_id)
#     db.add(db_item)
#     db.commit()
#     db.refresh(db_item)
#     return db_item
