from clearcode.config import config
from clearcode.observability.logger import get_logger


logger = get_logger(__name__)


def get_retriever():
   """Return the right retrieve function based on rag mode and vector_store in config."""
   mode = config["rag"]["mode"]
   vector_store = config["vector_store"]["vector_store"]


   if mode == "hybrid" and vector_store == "qdrant":
       from .hybrid_qdrant import retrieve
   elif vector_store == "qdrant":
       from .semantic_qdrant import retrieve
   else:
       from .semantic_chroma import retrieve


   return retrieve

