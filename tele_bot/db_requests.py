from sqlalchemy import insert, select
from database import engine, session_factory, Base
from models import players_table, Player


def create_tables():
    engine.echo = False
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.echo = True


def insert_data():
    with engine.connect() as connection:
        command = insert(players_table).values(
            [
                {'name': 'dnlskj'},
                {'name': 'sdfjvnls'},
            ]
        )
        connection.execute(command)
        connection.commit()


def insert_data_class():
    with session_factory() as session:
        worker_1 = Player(name='first')
        worker_2 = Player(name='second')
        session.add_all([worker_1, worker_2])
        session.commit()


def select_data():
    with session_factory() as session:
        command = select(Player)
        data = session.execute(command)
        players_data = data.scalars().all()
        print(f'{players_data=}')


def update_data(pk: int):
    with session_factory() as session:
        player = session.get(Player, pk)
        player.name = 'Dima'
        session.commit()
