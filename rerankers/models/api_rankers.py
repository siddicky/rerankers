from typing import Union, List, Optional
from rerankers.models.ranker import BaseRanker
from rerankers.results import RankedResults, Result
from rerankers.utils import ensure_docids, ensure_docs_list

import requests
import json
import os

URLS = {
    "cohere": "https://api.cohere.ai/v1/rerank",
    "jina": "https://api.jina.ai/v1/rerank",
    "mixedbread": NotImplemented,
}


class APIRanker(BaseRanker):

    def __init__(
        self,
        model: str,
        api_provider: str,
        verbose: int = 1,
        api_key: Optional[str] = None,
    ):
        if api_key is None:
            env_vars = ["COHERE_API_KEY", "JINA_API_KEY"]
            for env_var in env_vars:
                api_key = os.getenv(env_var)
                if api_key is not None:
                    break

        if api_key is None:
            raise ValueError(
                f"API key not provided and none of the environment variables {', '.join(env_vars)} are set"
            )

        self.api_key = api_key
        self.model = model
        self.api_provider = api_provider.lower()
        self.verbose = verbose
        self.ranking_type = "pointwise"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self.url = URLS[self.api_provider]

    def _parse_response(
        self, response: dict, doc_ids: Union[List[str], List[int]]
    ) -> RankedResults:
        ranked_docs = []
        if self.api_provider == "cohere" or self.api_provider == "jina":
            for i, r in enumerate(response["results"]):
                ranked_docs.append(
                    Result(
                        doc_id=doc_ids[r["index"]],
                        text=r["document"]["text"],
                        score=r["relevance_score"],
                        rank=i + 1,
                    )
                )

        return ranked_docs

    def rank(
        self,
        query: str,
        docs: Union[str, List[str]],
        doc_ids: Optional[Union[List[str], List[int]]] = None,
    ) -> RankedResults:
        docs = ensure_docs_list(docs)
        doc_ids = ensure_docids(doc_ids, len(docs))
        payload = self._format_payload(query, docs)
        response = requests.post(self.url, headers=self.headers, data=payload)
        results = self._parse_response(response.json(), doc_ids)
        return RankedResults(results=results, query=query, has_scores=True)

    def _format_payload(self, query: str, docs: List[str]) -> str:
        if self.api_provider == "cohere" or self.api_provider == "jina":
            return json.dumps(
                {
                    "model": self.model,
                    "query": query,
                    "documents": docs,
                    "top_n": len(docs),
                    "return_documents": True,
                }
            )

    def score(self, query: str, doc: str) -> float:
        payload = self._format_payload(query, [doc])
        response = requests.post(self.url, headers=self.headers, data=payload)
        results = self._parse_response(response.json(), [doc])
        return results[0].score
