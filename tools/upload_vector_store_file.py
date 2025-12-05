#!/usr/bin/env python3

"""
Upload File to Vector Store

This script uploads a file to the OpenAI vector store used by the Responses API.
Based on OpenAI API documentation for vector store file management.

Usage:
    python3 tools/upload_vector_store_file.py [file_path]

Example:
    python3 tools/upload_vector_store_file.py knowledge_base/database_txt/Course_Design_Overview_2025_07.txt
"""

import os
import sys
import time
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
load_dotenv()

def upload_file_to_vector_store(file_path: str = None, chunk_size: int = None, chunk_overlap: int = None):
    """
    Upload a file to the OpenAI vector store.
    
    Args:
        file_path: Path to the file to upload. If None, uses default Course Design Overview.
        chunk_size: Maximum tokens per chunk (for static chunking). If None, uses default/auto.
        chunk_overlap: Overlapping tokens between chunks (for static chunking). If None, uses default/auto.
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Get API key and vector store ID from environment
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable is required")
        print("   Please set this in your .env file or environment")
        return False
    
    vector_store_id = os.getenv('OPENAI_VECTOR_STORE_ID')
    if not vector_store_id:
        print("❌ Error: OPENAI_VECTOR_STORE_ID environment variable is required")
        print("   Please set this in your .env file or environment")
        return False
    
    # Initialize OpenAI client with explicit API key
    client = OpenAI(api_key=api_key)
    
    # Determine file path
    if file_path is None:
        file_path = "knowledge_base/database_txt/Course_Design_Overview_2025_07.txt"
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return False
    
    file_name = os.path.basename(file_path)
    print(f"📄 Uploading {file_name} to vector store...")
    print(f"📂 File path: {file_path}")
    print(f"🔗 Vector Store ID: {vector_store_id}")
    print()
    
    try:
        # Step 1: Upload file to OpenAI's file storage
        print("1️⃣ Uploading file to OpenAI file storage...")
        with open(file_path, 'rb') as file:
            file_response = client.files.create(
                file=file,
                purpose='assistants'
            )
        
        file_id = file_response.id
        print(f"   ✅ File uploaded successfully")
        print(f"   📋 File ID: {file_id}")
        print()
        
        # Step 2: Add file to vector store using direct HTTP API
        print("2️⃣ Adding file to vector store...")
        
        import urllib.request
        import urllib.parse
        import json
        
        # Prepare chunking strategy if specified
        chunking_strategy = None
        if chunk_size is not None:
            overlap = chunk_overlap if chunk_overlap is not None else int(chunk_size * 0.15)  # 15% default overlap
            chunking_strategy = {
                "type": "static",
                "static": {
                    "max_chunk_size_tokens": chunk_size,
                    "chunk_overlap_tokens": overlap
                }
            }
            print(f"   📏 Chunking: {chunk_size} tokens, {overlap} overlap")
        
        # Use individual file endpoint if chunking is specified, otherwise use batch endpoint
        if chunking_strategy:
            # Add file individually with chunking strategy
            url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/files"
            data = {
                'file_id': file_id,
                'chunking_strategy': chunking_strategy
            }
        else:
            # Use batch endpoint (default behavior)
            url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches"
            data = {
                'file_ids': [file_id]
            }
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'OpenAI-Beta': 'assistants=v2'
        }
        
        # Make the request
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                
                if chunking_strategy:
                    # Individual file endpoint returns file object directly
                    print(f"   ✅ File added to vector store with chunking")
                    print(f"   📋 File ID in vector store: {response_data.get('id', 'N/A')}")
                    print()
                    # For individual files, processing happens automatically
                    # Wait a moment for processing
                    time.sleep(2)
                    return True
                else:
                    # Batch endpoint returns batch object
                    batch_id = response_data['id']
                    print(f"   ✅ File batch created")
                    print(f"   📋 Batch ID: {batch_id}")
                    print()
        except Exception as e:
            print(f"   ❌ Failed to add file: {e}")
            return False
        
        # Step 3: Monitor batch status (only for batch endpoint)
        if not chunking_strategy:
        print("3️⃣ Monitoring upload progress...")
        max_attempts = 30  # Maximum wait time: 30 seconds
        attempt = 0
        
        while attempt < max_attempts:
            # Check batch status
            status_url = f"https://api.openai.com/v1/vector_stores/{vector_store_id}/file_batches/{batch_id}"
            status_req = urllib.request.Request(status_url, headers=headers)
            
            try:
                with urllib.request.urlopen(status_req) as response:
                    batch_status = json.loads(response.read().decode('utf-8'))
                    
                status = batch_status['status']
                file_counts = batch_status.get('file_counts', {})
                
                if status == "completed":
                    print(f"   ✅ Upload completed successfully!")
                    print(f"   📊 Files processed: {file_counts.get('completed', 0)}")
                    if file_counts.get('failed', 0) > 0:
                        print(f"   ⚠️  Files failed: {file_counts.get('failed', 0)}")
                    break
                elif status == "failed":
                    print(f"   ❌ Upload failed!")
                    print(f"   📊 Files failed: {file_counts.get('failed', 0)}")
                    return False
                elif status in ["in_progress", "queued"]:
                    print(f"   ⏳ Status: {status} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(1)
                    attempt += 1
                else:
                    print(f"   ❓ Unknown status: {status}")
                    time.sleep(1)
                    attempt += 1
                    
            except Exception as e:
                print(f"   ⚠️  Error checking status: {e}")
                time.sleep(1)
                attempt += 1
        
        if attempt >= max_attempts:
            print(f"   ⚠️  Upload monitoring timed out. Status may still be processing.")
            print(f"   💡 Check the OpenAI dashboard for final status.")
        
        print()
        print("🎉 Vector store update completed!")
        print(f"📍 The file '{file_name}' is now available in your vector store.")
        print(f"🔍 It will be searchable by the Responses API immediately.")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during upload: {str(e)}")
        print(f"💡 Common issues:")
        print(f"   - Check your OpenAI API key is valid")
        print(f"   - Ensure OPENAI_VECTOR_STORE_ID is correct")
        print(f"   - Verify the file format is supported (.txt, .md, .pdf)")
        print(f"   - Make sure the file has sufficient content")
        return False

def main():
    """Main function to handle command line usage"""
    print("🚀 OpenAI Vector Store File Upload Tool")
    print("=" * 50)
    
    # Check for command line argument
    file_path = None
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"📁 Using provided file path: {file_path}")
    else:
        print(f"📁 Using default file: Course_Design_Overview_2025_07.txt")
    
    print()
    
    # Execute upload
    success = upload_file_to_vector_store(file_path)
    
    if success:
        print("\n✅ SUCCESS: File uploaded to vector store!")
        sys.exit(0)
    else:
        print("\n❌ FAILED: Could not upload file to vector store!")
        sys.exit(1)

if __name__ == "__main__":
    main()
