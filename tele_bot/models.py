from typing import Annotated, Optional

from database import Base
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table
from sqlalchemy.orm import Mapped, mapped_column

meta = MetaData()

players_table = Table(
    'players',
    meta,
    Column('id', Integer, primary_key=True),
    Column('name', String)
)

intpk = Annotated[int, mapped_column(primary_key=True)]


class Room(Base):
    __tablename__ = 'rooms'
    id: Mapped[intpk]


class Player(Base):
    __tablename__ = 'players'
    id: Mapped[intpk]
    name: Mapped[str]
    room: Mapped[Optional[int]] = mapped_column(
        ForeignKey(Room.id, ondelete='CASCADE'),
        nullable=True
    )
