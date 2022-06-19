import os
import sqlite3
from datetime import date

from config import DB_NAME


class Database:

    def __enter__(self):
        self.__connection = sqlite3.connect(self._get_path())
        self.__cursor = self.__connection.cursor()
        self.__init_table()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__connection.commit()
        self.__connection.close()

    def _get_path(self) -> str:
        path = os.path.realpath(__file__)
        path = path.removesuffix(os.path.basename(__file__))
        path = os.path.join(path, DB_NAME)
        path = r"{}".format(path)
        return path

    def __init_table(self) -> None:
        self.__cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users(
                id INT PRIMARY KEY,
                UNIQUE(user_id)
            );
            
            CREATE TABLE IF NOT EXISTS subscriptions(
                tinkoff_token VARCHAR(100),
                broker_account_id INT PRIMARY KEY,
                broker_account_started_at DATE,
                UNIQUE(broker_id)
            );
            
            CREATE TABLE IF NOT EXISTS users_subscriptions(
                user_id INT,
                broker_account_id INT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(broker_account_id) REFERENCES subscriptions(broker_account_id),
                UNIQUE(user_id, broker_account_id)
            )
        """)

        self.__connection.commit()

    def add(self, user_id: int, tinkoff_token: str, broker_account_id: int, broker_account_started_at: date):
        self.__cursor.executescript(
            f"INSERT OR REPLACE INTO users (id) "
            f"VALUES ({user_id}); "
            f"INSERT OR REPLACE INTO subscriptions (broker_account_id, tinkoff_token, broker_account_started_at) "
            f"VALUES ({broker_account_id}, {tinkoff_token}, {broker_account_started_at}); "
            f"INSERT OR REPLACE INTO users_subscriptions (user_id, broker_account_id) "
            f"VALUES ({user_id}, {broker_account_id}); "
        )
        self.__connection.commit()

    def get(self, user_id: int) -> list:
        return self.__cursor.execute(
            f"SELECT user_id, tinkoff_token, broker_account_id, broker_account_started_at "
            f"FROM users AS u "
            f"INNER JOIN users_subscriptions AS us "
            f"ON us.user_id = u.id "
            f"INNER JOIN subscriptions AS s "
            f"ON us.broker_account_id = s.broker_account_id "
            f"WHERE id = {user_id}"
        ).fetchall()

    def get_user_ids(self) -> list:
        users = self.__cursor.execute(
            f"SELECT id "
            f"FROM users"
        ).fetchall()

        user_ids = []
        for user in users:
            user_ids.append(user[0])
        return user_ids

    def not_exists_key(self, user_id: int, broker_id: int) -> bool:
        found = self.__cursor.execute(f"SELECT * FROM users_subscriptions "
                                      f"WHERE user_id = {user_id} AND broker_account_id = {broker_id}").fetchone()
        return True if found is not None else False

    def delete(self, user_id: int, broker_id: int) -> None:
        self.__cursor.execute(
            f"DELETE FROM users_subscriptions "
            f"WHERE user_id = {user_id} AND broker_account_id = {broker_id}"
        )
        self.__connection.commit()

    def cmd(self) -> None:
        self.__cursor.execute("DROP TABLE users")
        self.__connection.commit()
