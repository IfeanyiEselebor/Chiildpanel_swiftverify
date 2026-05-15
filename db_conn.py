import os

import mysql.connector
from dotenv import load_dotenv

# Belt-and-braces: load .env here too in case db_start() is invoked from a
# script (cron, shell) that didn't go through app.py.
load_dotenv()


def db_start():
    """Establish a persistent database connection and return connection and cursor."""
    try:
        db = mysql.connector.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            database=os.environ["DB_NAME"],
            autocommit=True  # Automatically commit transactions
        )
        cur = db.cursor(dictionary=True)
        return db, cur  # Return active connection and cursor

    except mysql.connector.InterfaceError as e:
        print("InterfaceError: Issue with connection settings (network or DNS).")
        print(f"Error details: {e}")
    except mysql.connector.NotSupportedError as e:
        print("NotSupportedError: Unsupported MySQL feature used.")
        print(f"Error details: {e}")
    except mysql.connector.DataError as e:
        print("DataError: Invalid data type or out-of-range value.")
        print(f"Error details: {e}")
    except mysql.connector.OperationalError as e:
        print("OperationalError: MySQL is down, or authentication failed.")
        print(f"Error details: {e}")
    except mysql.connector.ProgrammingError as e:
        print("ProgrammingError: Invalid SQL syntax or database schema issue.")
        print(f"Error details: {e}")
    except mysql.connector.IntegrityError as e:
        print("IntegrityError: Duplicate key or constraint violation.")
        print(f"Error details: {e}")
    except mysql.connector.DatabaseError as e:
        print("DatabaseError: Problem with database connection.")
        print(f"Error details: {e}")
    except mysql.connector.Error as e:
        print("General MySQL Error: Something went wrong.")
        print(f"Error details: {e}")
    except Exception as e:
        print("Unexpected Error: An unknown issue occurred.")
        print(f"Error details: {e}")

    return None, None  # Return None if connection fails


# Create a Python object from the result
class User:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def get_wallet_balance(self):
        db, cur = db_start()
        try:
            # Define the query
            query = f"""
                SELECT 
                    IFNULL(
                        REPLACE(
                            FORMAT(
                                SUM(
                                    IF(type IN ('instant', 'manual') AND status = 'Finished', 
                                        amount, 
                                        IF(status IN ('Finished', 'Received'), 
                                            -amount, 
                                            0)
                                        )
                                ), 
                                2
                            ), 
                            ',', 
                            ''
                        ), 
                        '0.00'
                    ) AS balance
                FROM (
                    SELECT date, type, amount, NULL AS service, NULL AS country, status 
                    FROM transactions 
                    WHERE user_id = {self.user_id}
                    UNION ALL
                    SELECT date, NULL AS type, price AS amount, service, country, status 
                    FROM history 
                    WHERE user_id = {self.user_id}
                ) AS combined_result;
            """

            # Execute the query
            cur.execute(query)

            # Fetch the result
            balance = cur.fetchall()
            return balance[0]['balance']
        finally:
            cur.close()
            db.close()



class Otp:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Transaction:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class History:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class Admin:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
