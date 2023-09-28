from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLALCHEMY_DATABASE_URL = 'postgresql://kujgzuuz:5XzWRlq7pzKX3Wq5hhPvHHoxgPu7xp-n@rajje.db.elephantsql.com/kujgzuuz'


engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
