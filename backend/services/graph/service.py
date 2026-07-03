import json
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from domain.tenant.graph.models import Entity, Relationship, Community, DocumentSummary
from infra.llm.gemini import gemini_service

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
            
            # Embeddings lists
            ent_texts = []
            rel_texts = []
            comm_texts = []
            
            entities = data.get("entities", [])
            relationships = data.get("relationships", [])
            communities = data.get("communities", [])
            doc_summary = data.get("document_summary", "")
            
            # Entities
            for e in entities:
                ent_text = f"{e['name']} - {e['description']} - Aliases: {', '.join(e.get('aliases', []))}"
                ent_texts.append(ent_text)
                
            if ent_texts:
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
                    
            # Relationships
            ent_map = {e["id"]: e["name"] for e in entities}
            valid_rels = []
            for r in relationships:
                # We need source/target names for a rich relationship embedding
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
                    
            # Communities
            for c in communities:
                comm_texts.append(f"{c['name']} - {c['description']}")
                
            if comm_texts:
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
                    
            # Document Summary
            if doc_summary:
                sum_vec = await gemini_service.generate_embedding(doc_summary)
                ds_obj = DocumentSummary(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    summary=doc_summary,
                    embedding=sum_vec
                )
                db.add(ds_obj)
                
            await db.flush()
        except Exception as e:
            print(f"Graph extraction failed for chunk: {e}")
