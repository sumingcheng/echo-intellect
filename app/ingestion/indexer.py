import logging
import uuid
from dataclasses import dataclass

from app.llms.embeddings import embedding_manager
from app.models.data_models import Data, EmbeddingVector
from app.stores.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VectorJob:
    """一次向量化任务，对应一个Data的一种向量。"""

    id: str
    data_id: str
    text: str
    vector_type: str


class EmbeddingIndexer:
    """负责生成embedding并写入Qdrant。"""

    def __init__(self, qdrant_store: QdrantVectorStore, batch_size: int = 16):
        self.qdrant_store = qdrant_store
        self.batch_size = batch_size

    def index_data(self, data_list: list[Data]) -> dict[str, list[str]]:
        """批量向量化并返回 data_id -> vector_ids。"""
        vector_map: dict[str, list[str]] = {data.id: [] for data in data_list}
        jobs = self._build_jobs(data_list)

        for start in range(0, len(jobs), self.batch_size):
            batch = jobs[start : start + self.batch_size]
            embeddings = embedding_manager.embed_texts([job.text for job in batch])
            vectors = [
                EmbeddingVector(
                    id=job.id,
                    data_id=job.data_id,
                    vector=embedding,
                    model=embedding_manager.model,
                )
                for job, embedding in zip(batch, embeddings)
            ]

            if not self.qdrant_store.insert_vectors(vectors):
                raise RuntimeError("Qdrant向量写入失败")

            for job in batch:
                vector_map[job.data_id].append(job.id)

        logger.info("向量索引完成: data=%s, vectors=%s", len(data_list), len(jobs))
        return vector_map

    def _build_jobs(self, data_list: list[Data]) -> list[VectorJob]:
        jobs = []
        for data in data_list:
            jobs.append(
                VectorJob(
                    id=str(uuid.uuid4()),
                    data_id=data.id,
                    text=data.content,
                    vector_type="main",
                )
            )

            # 长文本保留一个子向量，提高局部召回。
            if len(data.content) > 512:
                jobs.append(
                    VectorJob(
                        id=str(uuid.uuid4()),
                        data_id=data.id,
                        text=data.content[:512],
                        vector_type="sub",
                    )
                )

        return jobs
