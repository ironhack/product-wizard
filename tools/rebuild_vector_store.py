#!/usr/bin/env python3

"""
Rebuild Vector Store with Custom Chunking

This script:
1. Empties the vector store (removes all files)
2. Configures chunking strategy (500 tokens with 75 token overlap)
3. Re-uploads all files from knowledge_base/database_txt/

Usage:
    python3 tools/rebuild_vector_store.py
    
    # With custom chunk size
    python3 tools/rebuild_vector_store.py --chunk-size 500 --overlap 75
    
    # Dry run (show what would be done without actually doing it)
    python3 tools/rebuild_vector_store.py --dry-run

Example:
    python3 tools/rebuild_vector_store.py
"""

import os
import sys
import time
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

def list_all_files(client, vector_store_id):
    """List all files currently in the vector store"""
    try:
        vector_store_files = client.vector_stores.files.list(
            vector_store_id
        )
        return vector_store_files.data if vector_store_files.data else []
    except Exception as e:
        print(f"⚠️  Error listing files: {e}")
        return []

def empty_vector_store(client, vector_store_id, dry_run=False, skip_confirmation=False):
    """Remove all files from the vector store"""
    print("🗑️  Emptying vector store...")
    print("=" * 60)
    
    files = list_all_files(client, vector_store_id)
    
    if not files:
        print("✅ Vector store is already empty")
        return True
    
    print(f"📋 Found {len(files)} files to remove")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would remove:")
        for file_obj in files:
            try:
                file_details = client.files.retrieve(file_obj.id)
                print(f"   - {file_details.filename} ({file_obj.id})")
            except:
                print(f"   - {file_obj.id}")
        return True
    
    # Confirm deletion (unless skipped)
    if not skip_confirmation:
        print("\n⚠️  WARNING: This will delete ALL files from the vector store!")
        confirmation = input("Type 'yes' to confirm: ")
        if confirmation.lower() != 'yes':
            print("❌ Operation cancelled")
            return False
    
    removed_count = 0
    failed_count = 0
    
    for file_obj in files:
        try:
            file_details = client.files.retrieve(file_obj.id)
            filename = file_details.filename
        except:
            filename = file_obj.id
        
        try:
            # Remove from vector store
            client.vector_stores.files.delete(
                file_id=file_obj.id,
                vector_store_id=vector_store_id
            )
            
            # Delete the file itself
            client.files.delete(file_obj.id)
            
            print(f"   ✅ Removed: {filename}")
            removed_count += 1
            
        except Exception as e:
            print(f"   ❌ Failed to remove {filename}: {e}")
            failed_count += 1
    
    print(f"\n📊 Removed {removed_count}/{len(files)} files")
    if failed_count > 0:
        print(f"⚠️  {failed_count} files failed to remove")
    
    return failed_count == 0

def configure_chunking(client, vector_store_id, chunk_size, overlap, dry_run=False):
    """Configure vector store chunking strategy"""
    print("\n⚙️  Configuring chunking strategy...")
    print("=" * 60)
    print(f"   Chunk Size: {chunk_size} tokens")
    print(f"   Overlap: {overlap} tokens ({overlap/chunk_size*100:.1f}%)")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would configure chunking")
        return True
    
    try:
        # Use HTTP API directly for chunking configuration (beta endpoint)
        import urllib.request
        
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
                    'max_chunk_size_tokens': chunk_size,
                    'chunk_overlap_tokens': overlap
                }
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='PATCH'
        )
        
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        print("✅ Chunking configured successfully")
        return True
    except Exception as e:
        print(f"❌ Error configuring chunking: {e}")
        print("💡 Trying alternative method...")
        
        # Alternative: Try using the OpenAI client's beta API if available
        try:
            # Check if beta API is available
            if hasattr(client, 'beta') and hasattr(client.beta, 'vector_stores'):
                client.beta.vector_stores.update(
                    vector_store_id,
                    chunking_strategy={
                        "type": "static",
                        "max_chunk_size_tokens": chunk_size,
                        "chunk_overlap_tokens": overlap
                    }
                )
                print("✅ Chunking configured successfully (alternative method)")
                return True
        except Exception as e2:
            print(f"❌ Alternative method also failed: {e2}")
        
        return False

def upload_file(client, vector_store_id, file_path, chunk_size=None, chunk_overlap=None):
    """Upload a single file to the vector store with optional chunking"""
    file_name = os.path.basename(file_path)
    
    try:
        # Step 1: Upload file to OpenAI
        with open(file_path, 'rb') as file:
            file_response = client.files.create(
                file=file,
                purpose='assistants'
            )
        file_id = file_response.id
        
        # Step 2: Add to vector store with chunking strategy if specified
        import urllib.request
        
        # Prepare chunking strategy if specified
        chunking_strategy = None
        if chunk_size is not None:
            overlap = chunk_overlap if chunk_overlap is not None else int(chunk_size * 0.15)
            chunking_strategy = {
                "type": "static",
                "static": {
                    "max_chunk_size_tokens": chunk_size,
                    "chunk_overlap_tokens": overlap
                }
            }
            # Use individual file endpoint with chunking
            url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files"
            data = {
                'file_id': file_id,
                'chunking_strategy': chunking_strategy
            }
        else:
            # Use batch endpoint (default)
            url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches"
            data = {'file_ids': [file_id]}
        
        headers = {
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
            'Content-Type': 'application/json',
            'OpenAI-Beta': 'assistants=v2'
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            
            if chunking_strategy:
                # Individual file endpoint - processing happens automatically
                # Wait a moment and return success
                time.sleep(2)
                return True, file_name
            else:
                # Batch endpoint - need to monitor status
                batch_id = response_data['id']
        
        # Step 3: Wait for processing (only for batch endpoint)
        if not chunking_strategy:
            max_attempts = 60  # 60 seconds max wait
            attempt = 0
            
            while attempt < max_attempts:
                status_url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}"
                status_req = urllib.request.Request(status_url, headers=headers)
                
                with urllib.request.urlopen(status_req) as response:
                    batch_status = json.loads(response.read().decode('utf-8'))
                    status = batch_status['status']
                    
                    if status == "completed":
                        return True, file_name
                    elif status == "failed":
                        return False, f"{file_name} (batch failed)"
                    elif status in ["in_progress", "queued"]:
                        time.sleep(1)
                        attempt += 1
                    else:
                        time.sleep(1)
                        attempt += 1
            
            return False, f"{file_name} (timeout)"
        
        return True, file_name
        
    except Exception as e:
        return False, f"{file_name} ({str(e)})"

def repopulate_vector_store(client, vector_store_id, chunk_size=None, chunk_overlap=None, dry_run=False):
    """Re-upload all files from knowledge_base/database_txt/"""
    print("\n📤 Re-populating vector store...")
    print("=" * 60)
    
    # Find all .txt files in knowledge_base/database_txt/
    txt_dir = Path(__file__).parent.parent / "knowledge_base" / "database_txt"
    
    if not txt_dir.exists():
        print(f"❌ Directory not found: {txt_dir}")
        return False
    
    txt_files = sorted(txt_dir.glob("*.txt"))
    
    if not txt_files:
        print(f"❌ No .txt files found in {txt_dir}")
        return False
    
    print(f"📋 Found {len(txt_files)} files to upload:")
    for txt_file in txt_files:
        print(f"   - {txt_file.name}")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would upload all files")
        return True
    
    print("\n⏳ Uploading files (this may take a while)...")
    
    uploaded_count = 0
    failed_files = []
    
    for idx, txt_file in enumerate(txt_files, 1):
        print(f"\n[{idx}/{len(txt_files)}] Uploading {txt_file.name}...", end=" ", flush=True)
        
        # Use chunking from args if available
        success, result = upload_file(
            client, 
            vector_store_id, 
            str(txt_file),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        if success:
            print("✅")
            uploaded_count += 1
        else:
            print(f"❌ {result}")
            failed_files.append(result)
    
    print("\n" + "=" * 60)
    print(f"📊 Upload Summary:")
    print(f"   ✅ Successfully uploaded: {uploaded_count}/{len(txt_files)}")
    if failed_files:
        print(f"   ❌ Failed: {len(failed_files)}")
        for failed in failed_files:
            print(f"      - {failed}")
    
    return uploaded_count == len(txt_files)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Rebuild vector store with custom chunking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Rebuild with default 500 token chunks
  %(prog)s
  
  # Custom chunk size and overlap
  %(prog)s --chunk-size 400 --overlap 50
  
  # Dry run (see what would happen)
  %(prog)s --dry-run
        """
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Maximum tokens per chunk (default: 500)'
    )
    
    parser.add_argument(
        '--overlap',
        type=int,
        default=75,
        help='Overlapping tokens between chunks (default: 75, ~15%%)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without actually doing it'
    )
    
    parser.add_argument(
        '--yes',
        action='store_true',
        help='Skip confirmation prompt (use with caution!)'
    )
    
    args = parser.parse_args()
    
    print("🚀 Vector Store Rebuild Tool")
    print("=" * 60)
    print(f"📋 Configuration:")
    print(f"   Chunk Size: {args.chunk_size} tokens")
    print(f"   Overlap: {args.overlap} tokens ({args.overlap/args.chunk_size*100:.1f}%)")
    if args.dry_run:
        print(f"   Mode: DRY RUN (no changes will be made)")
    print()
    
    # Initialize client
    result = get_openai_client()
    if not result:
        sys.exit(1)
    
    client, vector_store_id = result
    print(f"🔗 Vector Store ID: {vector_store_id}\n")
    
    # Step 1: Empty vector store
    if not empty_vector_store(client, vector_store_id, dry_run=args.dry_run, skip_confirmation=args.yes):
        print("\n❌ Failed to empty vector store")
        sys.exit(1)
    
    # Step 2: Re-populate with chunking specified during upload
    # Note: Chunking is set per-file during upload, not at vector store level
    if not repopulate_vector_store(client, vector_store_id, args.chunk_size, args.overlap, dry_run=args.dry_run):
        print("\n❌ Failed to re-populate vector store")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    if args.dry_run:
        print("🔍 DRY RUN COMPLETE - No changes were made")
    else:
        print("🎉 Vector store rebuild complete!")
        print(f"✅ All files uploaded with {args.chunk_size}-token chunks")
    print("=" * 60)

if __name__ == "__main__":
    main()
