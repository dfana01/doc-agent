from config import get_config
from llm import get_openai_client

_client = None


def get_client():
    global _client
    if _client is not None:
        return _client
    
    from opensearchpy import OpenSearch, RequestsHttpConnection
    config = get_config()
    
    if config.is_local:
        _client = OpenSearch(hosts=[{"host": "localhost", "port": 9200}], use_ssl=False)
        return _client
    
    import boto3
    from requests_aws4auth import AWS4Auth
    creds = boto3.Session().get_credentials()
    auth = AWS4Auth(creds.access_key, creds.secret_key, config.aws_region, "es", session_token=creds.token)
    
    _client = OpenSearch(
        hosts=[{"host": config.opensearch_endpoint, "port": 443}],
        http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection
    )
    return _client


def ensure_index(name: str) -> None:
    client = get_client()
    if client.indices.exists(index=name):
        return
    
    client.indices.create(index=name, body={
        "settings": {"index": {"knn": True}},
        "mappings": {
            "properties": {
                "document_id": {"type": "keyword"},
                "s3_path": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "text": {"type": "text"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": 1536,
                    "method": {"name": "hnsw", "space_type": "cosinesimil", "engine": "nmslib"}
                },
                "filename": {"type": "keyword"},
                "document_type": {"type": "keyword"},
                "processed_at": {"type": "date"}
            }
        }
    })


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    config = get_config()
    client = get_openai_client()
    resp = client.embeddings.create(model=config.embedding_model, input=texts)
    return [item.embedding for item in resp.data]


def index_chunks(doc_id: str, s3_path: str, chunks: list[str], embeddings: list[list[float]], metadata: dict) -> int:
    if not chunks:
        return 0
    
    client = get_client()
    index = get_config().opensearch_index
    ensure_index(index)
    
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        client.index(
            index=index,
            id=f"{doc_id}_{i}",
            body={
                "document_id": doc_id,
                "s3_path": s3_path,
                "chunk_index": i,
                "text": chunk,
                "embedding": emb,
                **metadata
            }
        )
    
    client.indices.refresh(index=index)
    return len(chunks)


def search(query: str, top_k: int = 5, document_id: str | None = None) -> list[dict]:
    config = get_config()
    client = get_client()
    index = config.opensearch_index
    
    if not client.indices.exists(index=index):
        return []
    
    query_embedding = generate_embeddings([query])[0]
    knn_query = {"knn": {"embedding": {"vector": query_embedding, "k": top_k}}}
    
    if document_id:
        search_body = {
            "size": top_k,
            "query": {"bool": {"must": [knn_query], "filter": [{"term": {"document_id": document_id}}]}}
        }
    else:
        search_body = {"size": top_k, "query": knn_query}
    
    response = client.search(index=index, body=search_body)
    
    return [
        {
            "document_id": hit["_source"].get("document_id"),
            "chunk_index": hit["_source"].get("chunk_index"),
            "text": hit["_source"].get("text"),
            "filename": hit["_source"].get("filename"),
            "s3_path": hit["_source"].get("s3_path"),
            "score": hit.get("_score", 0),
        }
        for hit in response["hits"]["hits"]
    ]

