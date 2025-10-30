""" database 연결 및 초기화 시키는 코드 """
import sqlite3
import faiss
from sentence_transformers import SentenceTransformer
import logging
from pathlib import Path
import pickle

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self,
                sqlite_db_path: str|None,
                faiss_db_path: str|None,
                embedding_model_path: str|None):
        self.sqlite_db_path = sqlite_db_path
        self.faiss_db_path = faiss_db_path
        self.embedding_model_path = embedding_model_path
    
    def initialization(self):
        self._init_sqlite()
        self._init_faiss()
        self._init_embedding_model()
        return self 
    
    def _init_sqlite(self):
        """ SQLite 초기화 """
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_db_path, check_same_thread= False)
            self.sqlite_conn.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"SQLite initailzation failed: {e}")    
            raise 
    
    def _init_faiss(self):
        "FAISS 초기화 "
        try:
            # FAISS index load
            faiss_index_path = Path(self.faiss_db_path) / "legal_documents.index"
            self.faiss_index = faiss.read_index(str(faiss_index_path))
            
            # FAISS Metadata loda 
            metadata_path = Path(self.faiss_db_path)  / "legal_metadata.pkl"
            with open(metadata_path, 'rb') as f:
                self.faiss_metadata = pickle.load(f)

            # 빠른 조회를 위한 chunk_id -> metadata dict 생성           
            self._faiss_meta_dict = {
                meta.get("chunk_id"): meta 
                for meta in self.faiss_metadata
            }
        except Exception as e:
            logger.error(f"FAISS initialization failed: {e}")
    
    def _init_embedding_model(self):
        try:
            if Path(self.embedding_model_path).exists():
                self.embedding_model = SentenceTransformer(self.embedding_model_path)
            else: 
                raise FileExistsError(f"Embedding model not found: {self.embedding_model_path}")
        except Exception as e:
            logger.error(f"Embedding model initialization failed: {e}")
            
        
        