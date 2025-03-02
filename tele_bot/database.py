from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


engine = create_engine(
    url='sqlite:///sqlite3.db',
    echo=True
)

session_factory = sessionmaker(engine)


class Base(DeclarativeBase):
    pass
