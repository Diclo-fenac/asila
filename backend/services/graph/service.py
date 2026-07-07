import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from domain.tenant.graph.models import Entity, Relationship, Community, DocumentSummary
from infra.llm.gemini import gemini_service
from core.logging.config import logger

async def _map_entities(entities: list, db: AsyncSession):
    """Generate embeddings for entities and insert into DB."""
    if not entities:
        return
    ent_texts = [f"{e['name']} - {e['description']} - Aliases: {', '.join(e.get('aliases', []))}" for e in entities]
    ent_embeddings = await gemini_service.generate_embeddings(ent_texts)
    for e, vec in zip(entities, ent_embeddings):
        ent_obj = Entity(
            id=e.get("id", str(uuid.uuid4())),
            name=e["name"],
            type=e["type"],
            description=e["description"],
            aliases=e.get("aliases", []),
            synonyms=e.get("synonyms", []),
            embedding=vec
        )
        db.add(ent_obj)

async def _map_relationships(relationships: list, entities: list, db: AsyncSession):
    """Generate embeddings for relationships and insert into DB."""
    if not relationships:
        return
    ent_map = {e["id"]: e["name"] for e in entities}
    rel_texts = []
    valid_rels = []
    for r in relationships:
        src = ent_map.get(r["source_id"], r["source_id"])
        tgt = ent_map.get(r["target_id"], r["target_id"])
        rel_texts.append(f"{src} {r['predicate']} {tgt}")
        valid_rels.append(r)
    
    if rel_texts:
        rel_embeddings = await gemini_service.generate_embeddings(rel_texts)
        for r, vec in zip(valid_rels, rel_embeddings):
            rel_obj = Relationship(
                source_id=r["source_id"],
                target_id=r["target_id"],
                predicate=r["predicate"],
                embedding=vec
            )
            db.add(rel_obj)

async def _map_communities(communities: list, db: AsyncSession):
    """Generate embeddings for communities and insert into DB."""
    if not communities:
        return
    comm_texts = [f"{c['name']} - {c['description']}" for c in communities]
    comm_embeddings = await gemini_service.generate_embeddings(comm_texts)
    for c, vec in zip(communities, comm_embeddings):
        comm_obj = Community(
            id=c.get("id", str(uuid.uuid4())),
            name=c["name"],
            description=c["description"],
            contains_node_ids=c.get("contains_node_ids", []),
            embedding=vec
        )
        db.add(comm_obj)

async def _map_document_summary(doc_summary: str, document_id: str, db: AsyncSession):
    """Generate embedding for document summary and insert into DB."""
    if not doc_summary:
        return
    sum_vec = await gemini_service.generate_embedding(doc_summary)
    ds_obj = DocumentSummary(
        id=str(uuid.uuid4()),
        document_id=document_id,
        summary=doc_summary,
        embedding=sum_vec
    )
    db.add(ds_obj)

async def extract_multi_representation_data(db: AsyncSession, text_chunks: list[str], document_id: str):
    for chunk in text_chunks:
        prompt = f"""
        Analyze the following text and extract a rich Knowledge Graph representation.
        Return ONLY valid JSON matching this schema exactly:
        {{
            "entities": [
                {{"id": "unique-uuid", "name": "Name", "type": "Type", "description": "Detailed description", "aliases": ["alias1"], "synonyms": ["syn1"]}}
            ],
            "relationships": [
                {{"source_id": "uuid1", "target_id": "uuid2", "predicate": "USES"}}
            ],
            "communities": [
                {{"id": "unique-uuid", "name": "Cluster Name", "description": "What this cluster is about", "contains_node_ids": ["uuid1", "uuid2"]}}
            ],
            "document_summary": "A 2-sentence summary of this chunk"
        }}
        Text: {chunk}
        """
        try:
            data = await gemini_service.generate_json(prompt)

            async with db.begin_nested():
                entities = data.get("entities", [])
                relationships = data.get("relationships", [])
                communities = data.get("communities", [])
                doc_summary = data.get("document_summary", "")

                await _map_entities(entities, db)
                await _map_relationships(relationships, entities, db)
                await _map_communities(communities, db)
                await _map_document_summary(doc_summary, document_id, db)

                await db.flush()
        except Exception as e:
            logger.error(f"Graph extraction failed for chunk: {e}")
