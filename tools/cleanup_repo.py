#!/usr/bin/env python3
"""
Clean up repository by removing old test files and organizing remaining files
"""

import os
import shutil
import glob

def cleanup_old_files():
    """Remove old test files and move remaining files to appropriate locations"""
    
    print("🧹 Cleaning up repository...")
    print("=" * 30)
    
    # Files to remove (old test files that are no longer needed)
    files_to_remove = [
        "test_v4_final.py",
        "additional_models_test.json",
        "citation_test_results.json", 
        "model_comparison_results.json",
        "sales_test_results.json",
        "test_report.json",
        "v2_test_results.json",
        "v4_fabrication_test_results.json"
    ]
    
    # Remove old files
    removed_count = 0
    for filename in files_to_remove:
        if os.path.exists(filename):
            try:
                os.remove(filename)
                print(f"✅ Removed: {filename}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Error removing {filename}: {e}")
    
    if removed_count == 0:
        print("✅ No old files found to remove")
    else:
        print(f"✅ Removed {removed_count} old files")
    
    # Move any remaining test JSON files to results directory
    json_files = glob.glob("*.json")
    test_json_files = [f for f in json_files if "test" in f.lower() or "result" in f.lower()]
    
    if test_json_files:
        print(f"\n📁 Moving {len(test_json_files)} test result files to tests/results/")
        results_dir = "tests/results"
        os.makedirs(results_dir, exist_ok=True)
        
        for json_file in test_json_files:
            try:
                shutil.move(json_file, os.path.join(results_dir, json_file))
                print(f"✅ Moved: {json_file} → tests/results/")
            except Exception as e:
                print(f"❌ Error moving {json_file}: {e}")
    
    print(f"\n🎯 Repository cleanup complete!")

def verify_structure():
    """Verify the new repository structure is correct"""
    
    print(f"\n🔍 Verifying repository structure...")
    print("=" * 35)
    
    expected_structure = {
        "docs/reports": ["FINAL_REPORT.md", "CITATIONS_FINAL_REPORT.md", "MODEL_COMPARISON_FINAL.md"],
        "docs/development": ["MASTER_PROMPT_V2.md", "MASTER_PROMPT_V3.md", "MASTER_PROMPT_V4.md"],
        "tests": ["test_citations_clean.py"],
        "tests/model_tests": ["model_comparison_test.py", "update_and_test.py", "upgrade_to_gpt4o.py"],
        "tools": ["test_utils.py", "assistant_tester.py", "fix_assistant.py"]
    }
    
    all_good = True
    
    for directory, expected_files in expected_structure.items():
        print(f"\n📁 Checking {directory}/")
        
        if not os.path.exists(directory):
            print(f"❌ Directory missing: {directory}")
            all_good = False
            continue
        
        for expected_file in expected_files:
            file_path = os.path.join(directory, expected_file)
            if os.path.exists(file_path):
                print(f"  ✅ {expected_file}")
            else:
                print(f"  ⚠️ Missing: {expected_file}")
    
    # Check main files
    main_files = ["app.py", "MASTER_PROMPT.md", "config.py", "config.example.py", "README.md"]
    print(f"\n📄 Checking main files:")
    
    for main_file in main_files:
        if os.path.exists(main_file):
            print(f"  ✅ {main_file}")
        else:
            print(f"  ⚠️ Missing: {main_file}")
            if main_file != "config.py":  # config.py is created by user
                all_good = False
    
    if all_good:
        print(f"\n🎉 Repository structure is perfect!")
    else:
        print(f"\n⚠️ Some issues found in repository structure")
    
    return all_good

def show_new_structure():
    """Show the new organized repository structure"""
    
    print(f"\n📊 New Repository Structure:")
    print("=" * 30)
    
    def print_tree(directory, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
            
        try:
            items = sorted(os.listdir(directory))
            directories = [item for item in items if os.path.isdir(os.path.join(directory, item)) and not item.startswith('.')]
            files = [item for item in items if os.path.isfile(os.path.join(directory, item)) and not item.startswith('.')]
            
            # Show directories first
            for i, dir_name in enumerate(directories):
                is_last_dir = i == len(directories) - 1 and len(files) == 0
                print(f"{prefix}{'└── ' if is_last_dir else '├── '}{dir_name}/")
                extension = "    " if is_last_dir else "│   "
                print_tree(os.path.join(directory, dir_name), prefix + extension, max_depth, current_depth + 1)
            
            # Show files
            for i, file_name in enumerate(files):
                if file_name in ['config.py', '.env']:  # Skip sensitive files
                    continue
                is_last = i == len(files) - 1
                print(f"{prefix}{'└── ' if is_last else '├── '}{file_name}")
                
        except PermissionError:
            print(f"{prefix}[Permission Denied]")
    
    print_tree(".")

def main():
    print("🧹 Repository Organization Tool")
    print("=" * 35)
    
    # Cleanup old files
    cleanup_old_files()
    
    # Verify structure
    verify_structure()
    
    # Show new structure
    show_new_structure()
    
    print(f"\n✅ Repository organization complete!")
    print(f"\n📋 Next steps:")
    print(f"   1. Copy config.example.py to config.py")
    print(f"   2. Fill in your API credentials in config.py")
    print(f"   3. Test with: python3 tests/test_citations_clean.py")
    print(f"   4. Run main app with: python3 app.py")

if __name__ == "__main__":
    main()
