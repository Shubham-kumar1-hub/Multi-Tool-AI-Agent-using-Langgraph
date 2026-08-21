# setup_vector_store.py
# One-time setup for the pgvector table that will store PDF chunks.

# Windows uses ProactorEventLoop by default.
# Psycopg async connections require the Selector event loop instead.
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import Column, PGEngine, PGVectorStore

load_dotenv()

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from your .env file.")


# PGEngine uses SQLAlchemy's PostgreSQL URL format.
# normal psycopg URL starts with postgresql://,
# while SQLAlchemy + psycopg needs postgresql+psycopg://.
sqlalchemy_database_url = database_url.replace(
    "postgresql://",
    "postgresql+psycopg://",
    1,
) 


embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# PGEngine manages a reusable PostgreSQL connection pool.
pg_engine = PGEngine.from_connection_string(
    url = sqlalchemy_database_url
)

# Creates the table once.
# thread_id is a normal PostgreSQL column, so later every RAG search
# can retrieve only chunks belonging to the current chat thread.
pg_engine.init_vectorstore_table(
    table_name="document_chunks",
    vector_size=384,
    metadata_columns=[
        Column(name="thread_id", data_type="TEXT", nullable=False)
    ],
)

# Creates a LangChain vector-store object connected to that table.
# We will use this exact store in Agent_backend.py in the next step.
vector_store = PGVectorStore.create_sync(
    engine=pg_engine,
    table_name="document_chunks",
    embedding_service=embeddings,
    metadata_columns=["thread_id"],
)


print("pgvector table 'document_chunks' was created successfully.")
print("Embedding dimension: 384")