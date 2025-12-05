#!/usr/bin/env python3

"""
Configure Vector Store Chunking Strategy

OpenAI vector stores support two chunking strategies:
1. Auto (default) - Automatic chunking based on document structure
2. Static - Manual control with max_chunk_size_tokens and chunk_overlap_tokens

This script allows you to configure or update the chunking strategy for your vector store.

Usage:
    # Use auto chunking (default)
    python3 tools/configure_vector_store_chunking.py --auto
    
    # Use static chunking with custom parameters
    python3 tools/configure_vector_store_chunking.py --static --max-tokens 800 --overlap 200
    
    # Check current chunking configuration
    python3 tools/configure_vector_store_chunking.py --check

Examples:
    # Default auto chunking
    python3 tools/configure_vector_store_chunking.py --auto
    
    # Custom static chunking (800 tokens per chunk, 200 token overlap)
    python3 tools/configure_vector_store_chunking.py --static --max-tokens 800 --overlap 200
    
    # Smaller chunks for better precision (400 tokens, 10% overlap)
    python3 tools/configure_vector_store_chunking.py --static --max-tokens 400 --overlap 40
"""

import os
import sys
import json
import argparse
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def get_openai_client():
    """Initialize OpenAI client with API key validation"""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        return None
    
    vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
    if not vector_store_id:
        print("❌ Error: OPENAI_VECTOR_STORE_ID environment variable is required")
        return None
    
    client = OpenAI(api_key=api_key)
    return client, vector_store_id

def check_chunking_config(client, vector_store_id):
    """Check current chunking configuration of vector store"""
    try:
        vector_store = client.beta.vector_stores.retrieve(vector_store_id)
        
        chunking_strategy = vector_store.chunking_strategy
        print("📊 Current Chunking Configuration:")
        print(f"   Strategy: {chunking_strategy.type if hasattr(chunking_strategy, 'type') else 'Unknown'}")
        
        if hasattr(chunking_strategy, 'max_chunk_size_tokens'):
            print(f"   Max Chunk Size: {chunking_strategy.max_chunk_size_tokens} tokens")
        if hasattr(chunking_strategy, 'chunk_overlap_tokens'):
            print(f"   Chunk Overlap: {chunking_strategy.chunk_overlap_tokens} tokens")
        
        return chunking_strategy
        
    except Exception as e:
        print(f"❌ Error checking chunking config: {e}")
        return None

def update_chunking_auto(client, vector_store_id):
    """Update vector store to use auto chunking strategy"""
    try:
        print("🔄 Updating vector store to use AUTO chunking strategy...")
        
        # Use HTTP API directly (beta endpoint)
        import urllib.request
        import json
        
        url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}"
        headers = {
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
            'Content-Type': 'application/json',
            'OpenAI-Beta': 'assistants=v2'
        }
        
        data = {
            'chunking_strategy': {
                'type': 'auto'
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print("✅ Successfully updated to AUTO chunking strategy")
        print("   OpenAI will automatically determine optimal chunk boundaries")
        return True
        
    except Exception as e:
        print(f"❌ Error updating chunking config: {e}")
        return False

def update_chunking_static(client, vector_store_id, max_tokens, overlap_tokens):
    """Update vector store to use static chunking strategy"""
    try:
        print(f"🔄 Updating vector store to use STATIC chunking strategy...")
        print(f"   Max Chunk Size: {max_tokens} tokens")
        print(f"   Chunk Overlap: {overlap_tokens} tokens")
        
        # Validate parameters
        if max_tokens < 100:
            print("⚠️  Warning: Max chunk size is very small (< 100 tokens)")
        if max_tokens > 2000:
            print("⚠️  Warning: Max chunk size is very large (> 2000 tokens)")
        
        overlap_percent = (overlap_tokens / max_tokens) * 100
        if overlap_percent > 50:
            print("⚠️  Warning: Overlap is > 50% of chunk size (may create redundancy)")
        elif overlap_percent < 5:
            print("⚠️  Warning: Overlap is < 5% (may lose context at boundaries)")
        
        # Use HTTP API directly (beta endpoint)
        import urllib.request
        import json
        
        url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}"
        headers = {
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
            'Content-Type': 'application/json',
            'OpenAI-Beta': 'assistants=v2'
        }
        
        data = {
            'chunking_strategy': {
                'type': 'static',
                'static': {
                    'max_chunk_size_tokens': max_tokens,
                    'chunk_overlap_tokens': overlap_tokens
                }
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print("✅ Successfully updated to STATIC chunking strategy")
        print("💡 Note: You may need to re-upload files for chunking changes to take effect")
        return True
        
    except Exception as e:
        print(f"❌ Error updating chunking config: {e}")
        print("💡 Note: You may need to re-upload files for chunking changes to take effect")
        return False

def main():
    """Main function to handle command line usage"""
    parser = argparse.ArgumentParser(
        description="Configure OpenAI vector store chunking strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use auto chunking (default)
  %(prog)s --auto
  
  # Use static chunking with custom parameters
  %(prog)s --static --max-tokens 800 --overlap 200
  
  # Smaller chunks for better precision
  %(prog)s --static --max-tokens 400 --overlap 40
  
  # Check current configuration
  %(prog)s --check
        """
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Use automatic chunking strategy (default)'
    )
    
    parser.add_argument(
        '--static',
        action='store_true',
        help='Use static chunking strategy with manual control'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        default=800,
        help='Maximum tokens per chunk (for static strategy, default: 800)'
    )
    
    parser.add_argument(
        '--overlap',
        type=int,
        default=200,
        help='Overlapping tokens between chunks (for static strategy, default: 200)'
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check current chunking configuration'
    )
    
    args = parser.parse_args()
    
    print("🔧 OpenAI Vector Store Chunking Configuration Tool")
    print("=" * 60)
    
    # Initialize client
    result = get_openai_client()
    if not result:
        sys.exit(1)
    
    client, vector_store_id = result
    print(f"🔗 Vector Store ID: {vector_store_id}\n")
    
    # Check current config
    if args.check:
        check_chunking_config(client, vector_store_id)
        sys.exit(0)
    
    # Update to auto
    if args.auto:
        success = update_chunking_auto(client, vector_store_id)
        if success:
            print("\n💡 Note: Existing files may need to be re-uploaded for changes to take effect")
        sys.exit(0 if success else 1)
    
    # Update to static
    if args.static:
        success = update_chunking_static(client, vector_store_id, args.max_tokens, args.overlap)
        if success:
            print("\n💡 Note: Existing files may need to be re-uploaded for changes to take effect")
        sys.exit(0 if success else 1)
    
    # No action specified
    print("❌ No action specified. Use --auto, --static, or --check")
    parser.print_help()
    sys.exit(1)

if __name__ == "__main__":
    main()
