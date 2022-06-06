import os
import sqlite3

from config import DB_NAME


class Database:
    def __enter__(self):
        self.__connection = sqlite3.connect(self.__get_path())
        self.__init_table()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__connection.close()

    def __get_path(self) -> str:
        path = os.path.realpath(__file__)
        path = path.removesuffix(os.path.basename(__file__))
        path = os.path.join(path, DB_NAME)
        path = r"{}".format(path)
        return path

    def __init_table(self) -> None:
        self.__connection.executescript("""
            CREATE TABLE IF NOT EXISTS stocks_packages(
                ticker VARCHAR(15),
                amount INT,
                cost REAL,
                UNIQUE(ticker)
            );
        """)
        self.__connection.commit()

    def add_stocks(self, ticker: str, amount: int, cost: float) -> None:
        self.__connection.execute(f"""
            INSERT INTO stocks_packages(ticker, amount, cost)
            VALUES (?, ?, ?);
        """, (ticker, amount, cost))
        self.__connection.commit()

    def get_stocks(self, ticker: str) -> tuple:
        return self.__connection.execute(f"""
                SELECT ticker, amount, cost
                FROM stocks_packages
                WHERE ticker = ?
            """, (ticker,)).fetchone()

    def get_stocks_packages(self) -> list:
        return self.__connection.execute("""
                SELECT ticker, amount, cost
                FROM stocks_packages
            """).fetchall()

    def update_stocks(self, ticker: str, amount: int, cost: float) -> None:
        self.__connection.execute(f"""
            UPDATE stocks_packages
            SET amount = ?,
                cost = ?
            WHERE ticker = ?;
        """, (amount, cost, ticker))
        self.__connection.commit()

    def delete_stocks(self, ticker: str) -> None:
        self.__connection.execute(f"""
            DELETE FROM stocks_packages
            WHERE ticker = ?
        """, (ticker,))
        self.__connection.commit()

    def cmd(self):
        self.__connection.execute(f"""DROP TABLE stocks_packages""")
        self.__connection.commit()
