#!/usr/bin/env python3

"""
Single-Query Debug Tester for Custom RAG Pipeline

Usage:
  python3 tests/single_query_debug_test.py --query "<your question here>"

This script runs the full pipeline for a single question and prints:
1) Retrieval inputs and results (files, scores, snippets)
2) Variant analysis and whether variant QA would trigger
3) Generation inputs and final response
4) Validation block with confidence and findings

Optionally saves a JSON of all artifacts with --save-results.
"""

import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Ensure project root on path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Avoid Slack initialization in tests
os.environ['SLACK_BOT_TOKEN'] = 'xoxb-test-token-for-testing'
os.environ['SLACK_SIGNING_SECRET'] = 'test-signing-secret-for-testing'


def initialize_pipeline():
    try:
        import openai
        from src.app_custom_rag import CustomRAGPipeline

        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
        with open('assistant_config/MASTER_PROMPT.md', 'r') as f:
            master_prompt = f.read()
        return CustomRAGPipeline(client, vector_store_id, master_prompt)
    except Exception as e:
        raise Exception(f"Failed to initialize pipeline: {e}")


def run_single_query_debug(query: str, save_results: bool = False):
    print("\n🧪 Single-Query Debug Test")
    print("=" * 60)
    print(f"Query: {query}")
    print("-" * 60)

    pipeline = initialize_pipeline()

    artifacts = {
        "query": query,
        "retrieval": {},
        "variant_analysis": {},
        "generation": {},
        "validation": {},
        "timestamps": {"started": datetime.utcnow().isoformat()}
    }

    # 1) Retrieval (with full introspection)
    print("1) Retrieving documents...")
    # Show enhanced query and instructions
    try:
        enhanced_query = pipeline._enhance_query_with_context(query, None)
        instructions = pipeline._get_retrieval_instructions(enhanced_query)
        print(f"   Enhanced query: {enhanced_query}")
        print(f"   Retrieval instructions len: {len(instructions or '')}")
        artifacts.setdefault("retrieval", {})["enhanced_query"] = enhanced_query
        artifacts["retrieval"]["instructions"] = instructions
    except Exception as e:
        print(f"   ⚠️ Could not inspect enhanced query/instructions: {e}")

    # Raw vector search hits (scores + previews)
    try:
        raw_resp = pipeline.client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": enhanced_query if 'enhanced_query' in locals() else query}],
            instructions=instructions if 'instructions' in locals() else None,
            tools=[{"type": "file_search", "vector_store_ids": [pipeline.vector_store_id], "max_num_results": 40}],
            tool_choice={"type": "file_search"},
            include=["file_search_call.results"]
        )
        hits = []
        for out in getattr(raw_resp, "output", []):
            res = getattr(out, "results", None)
            if res:
                hits = res
                break
            fsc = getattr(out, "file_search_call", None)
            if fsc:
                if getattr(fsc, "results", None):
                    hits = fsc.results
                    break
                if getattr(fsc, "search_results", None):
                    hits = fsc.search_results
                    break
        raw_list = []
        for r in hits[:20]:
            fname = getattr(r, "filename", None) or getattr(getattr(r, "document", None), "filename", None)
            fid = getattr(r, "file_id", None) or getattr(getattr(r, "document", None), "id", None)
            score = float(getattr(r, "score", 0.0) or 0.0)
            text = ""
            if hasattr(r, "text") and r.text:
                text = r.text
            else:
                parts = getattr(r, "content", []) or []
                if parts and hasattr(parts[0], "text"):
                    text = parts[0].text
                else:
                    content = getattr(getattr(r, "document", None), "content", None)
                    if content:
                        text = content
            raw_list.append({
                "filename": fname,
                "file_id": fid,
                "score": score,
                "preview": (text or "")[:200]
            })
        # Sort raw hits by score desc for readability
        raw_list_sorted = sorted(raw_list, key=lambda h: h.get("score", 0.0), reverse=True)
        artifacts["retrieval"]["raw_hits"] = raw_list_sorted
        print(f"   Raw hits (top {len(raw_list_sorted)}), sorted by score:")
        for i, h in enumerate(raw_list_sorted, 1):
            print(f"     {i}. {h['filename']}  score={h['score']:.4f}")
    except Exception as e:
        print(f"   ⚠️ Could not log raw vector hits: {e}")

    retrieved_docs, sources = pipeline.retrieve_documents(query)
    artifacts["retrieval"]["num_docs"] = len(retrieved_docs)
    artifacts["retrieval"]["sources"] = sources

    print(f"   Retrieved {len(retrieved_docs)} docs from {len(sources)} sources")
    print(f"   Sources: {sources}")
    for i, doc in enumerate(retrieved_docs[:5]):
        snippet = doc[:200].replace("\n", " ")
        print(f"   Doc {i+1} snippet: {snippet}...")

    # 2) Variant analysis
    print("\n2) Analyzing variants...")
    by_variant = pipeline._by_variant()
    artifacts["variant_analysis"]["by_variant"] = {k: [f for _, f in v] for k, v in by_variant.items()}
    concrete = [v for v in by_variant.keys() if v != "unspecified"]
    artifacts["variant_analysis"]["concrete_variants"] = concrete
    artifacts["variant_analysis"]["would_trigger_variant_qa"] = len(concrete) > 1

    print(f"   Variants: {list(by_variant.keys())}")
    for v, files in by_variant.items():
        print(f"   {v}: {[f for _, f in files]}")
    print(f"   Would trigger variant QA: {len(concrete) > 1}")

    # 3) Generation (pre-validation)
    print("\n3) Generation (pre-validation)...")
    result = pipeline.process_query(query)
    response = result.get('response', '')
    pre_validation_response = result.get('pre_validation_response', '')
    processing_time = result.get('processing_time', 0.0)
    sources_block = result.get('sources_block', '')

    artifacts["generation"]["pre_validation_response"] = pre_validation_response
    artifacts["generation"]["response"] = response
    artifacts["generation"]["processing_time"] = processing_time
    artifacts["generation"]["sources_block"] = sources_block

    if pre_validation_response:
        print(f"   Pre-validation response ({len(pre_validation_response)} chars): {pre_validation_response[:400]}...")
    print(f"   Processing time: {processing_time:.2f}s")
    if sources_block:
        print("   Sources block present in final response")

    # Evidence chunks overview
    try:
        ev = getattr(pipeline, "_evidence_chunks", []) or []
        ev_files = sorted(list({c.get("filename") for c in ev if c.get("filename")}))
        print(f"   Evidence chunks: {len(ev)} from files: {ev_files}")
        artifacts.setdefault("generation", {})["evidence_chunks_count"] = len(ev)
        artifacts["generation"]["evidence_files"] = ev_files
    except Exception as e:
        print(f"   ⚠️ Could not inspect evidence chunks: {e}")

    # 4) Validation
    print("\n4) Validation results...")
    validation = result.get('validation', {})
    pre_validation = result.get('pre_validation', {})
    artifacts["validation"] = validation
    artifacts["pre_validation"] = pre_validation
    if pre_validation:
        print("Original validator output (on pre-validation response):")
        print(json.dumps(pre_validation, indent=2))
    print("Final validation block (post-fallback if applied):")
    print(json.dumps(validation, indent=2))
    if pre_validation:
        print("\nPre-validation (original) result:")
        print(json.dumps(pre_validation, indent=2))

    # 5) Validator inputs meta
    try:
        ev = getattr(pipeline, "_evidence_chunks", []) or []
        evidence_text = "\n\n".join(c["text"] for c in ev) if ev else "\n\n".join(retrieved_docs)
        contrib_files = sorted(list({c.get("filename") for c in ev if c.get("filename")})) if ev else sources
        artifacts["validation_meta"] = {
            "evidence_chars": len(evidence_text or ""),
            "contributing_files": contrib_files
        }
        print(f"   Evidence size: {artifacts['validation_meta']['evidence_chars']} chars")
        print(f"   Contributing files: {artifacts['validation_meta']['contributing_files']}")
    except Exception as e:
        print(f"   ⚠️ Could not collect validation meta: {e}")

    # 6) Final response (post-validation)
    print("\n6) Final response (post-validation)...")
    print(f"   Response ({len(response)} chars): {response[:400]}...")

    artifacts["timestamps"]["finished"] = datetime.utcnow().isoformat()

    # Save JSON results if requested
    if save_results:
        results_dir = Path(__file__).parent / 'results'
        results_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        out_path = results_dir / f"single_query_debug_{ts}.json"
        with open(out_path, 'w') as f:
            json.dump(artifacts, f, indent=2)
        print(f"\n💾 Saved results to {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Run a single-query debug test through the pipeline")
    parser.add_argument('--query', required=True, help='The user question to debug')
    parser.add_argument('--save-results', action='store_true', help='Save a JSON with all artifacts')
    args = parser.parse_args()

    run_single_query_debug(args.query, save_results=args.save_results)


if __name__ == "__main__":
    main()


