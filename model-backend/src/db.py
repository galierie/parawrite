from dotenv import load_dotenv
from os import getenv
from sqlmodel import create_engine, SQLModel, Session, Field
from sqlalchemy.orm import declared_attr
from pydantic.alias_generators import to_snake

load_dotenv()

DATABASE_URL = getenv('DATABASE_URL')

if DATABASE_URL is None:
  raise ValueError('There\'s no database URL set.')

engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
  SQLModel.metadata.create_all(engine)

def db_init():
  with Session(engine) as session:
    yield session

class Base(SQLModel):
  @declared_attr.directive
  def __tablename__(cls) -> str: # type: ignore
    return to_snake(cls.__name__)

# ----- ORM -----

class Rating(Base, table=True):
  id: int | None = Field(default=None, primary_key=True)
  rating: int