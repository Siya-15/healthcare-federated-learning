import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from .env")

database_url = database_url.strip()

try:
    parsed_url = make_url(database_url)
except Exception as error:
    raise RuntimeError(
        "DATABASE_URL exists but is not a valid PostgreSQL URL. "
        "Check its formatting and URL-encode the password."
    ) from error

print("Driver:", parsed_url.drivername)
print("Host:", parsed_url.host)
print("Database:", parsed_url.database)
print("Username:", parsed_url.username)
print("Password present:", parsed_url.password is not None)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

try:
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), current_user, NOW()")
        )

        print("Connection successful!")
        print(result.one())
finally:
    engine.dispose()