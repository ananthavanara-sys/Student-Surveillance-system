"""
Script to populate class/section fields for existing students.
Use this if you have existing students without class/section data.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.database import get_db_context
from src.db.repository import FaceRepository
from src.db.models import Person


def populate_class_sections_interactive():
    """Interactively assign class/section to existing students."""
    with get_db_context() as db:
        repo = FaceRepository(db)
        persons = repo.get_all_persons()
        
        if not persons:
            print("No students found in database.")
            return
        
        print(f"Found {len(persons)} students without class/section data.\n")
        print("You can assign class and section to each student.")
        print("Press Enter to skip any student.\n")
        
        updated_count = 0
        
        for person in persons:
            # Skip if already has class/section
            if person.class_name and person.section_name:
                continue
            
            print(f"\n{'='*60}")
            print(f"Student: {person.name}")
            print(f"Current - Class: {person.class_name or 'None'}, Section: {person.section_name or 'None'}")
            
            class_name = input("Enter class (e.g., 10th) or press Enter to skip: ").strip()
            section_name = input("Enter section (e.g., A) or press Enter to skip: ").strip()
            
            if class_name or section_name:
                person.class_name = class_name if class_name else person.class_name
                person.section_name = section_name if section_name else person.section_name
                db.commit()
                updated_count += 1
                print(f"✓ Updated {person.name}: Class={person.class_name}, Section={person.section_name}")
        
        print(f"\n{'='*60}")
        print(f"✅ Updated {updated_count} students.")


def populate_class_sections_batch(mapping: dict):
    """
    Batch assign class/section based on a mapping dictionary.
    
    Args:
        mapping: Dict of {student_name: {"class": "10th", "section": "A"}}
    """
    with get_db_context() as db:
        repo = FaceRepository(db)
        updated_count = 0
        not_found = []
        
        for name, data in mapping.items():
            person = repo.get_person_by_name(name)
            if person:
                person.class_name = data.get("class")
                person.section_name = data.get("section")
                db.commit()
                updated_count += 1
                print(f"✓ Updated {name}: Class={person.class_name}, Section={person.section_name}")
            else:
                not_found.append(name)
        
        print(f"\n✅ Updated {updated_count} students.")
        if not_found:
            print(f"⚠️  Not found: {', '.join(not_found)}")


def show_current_distribution():
    """Display current class/section distribution."""
    with get_db_context() as db:
        repo = FaceRepository(db)
        persons = repo.get_all_persons()
        
        print("\n" + "="*60)
        print("CURRENT CLASS/SECTION DISTRIBUTION")
        print("="*60)
        
        # Count by class
        class_counts = {}
        section_counts = {}
        no_class = 0
        no_section = 0
        
        for person in persons:
            if person.class_name:
                class_counts[person.class_name] = class_counts.get(person.class_name, 0) + 1
            else:
                no_class += 1
            
            if person.section_name:
                section_counts[person.section_name] = section_counts.get(person.section_name, 0) + 1
            else:
                no_section += 1
        
        print(f"\nTotal Students: {len(persons)}")
        print(f"Without Class: {no_class}")
        print(f"Without Section: {no_section}")
        
        print("\nBy Class:")
        for cls in sorted(class_counts.keys()):
            print(f"  {cls}: {class_counts[cls]} students")
        
        print("\nBy Section:")
        for sec in sorted(section_counts.keys()):
            print(f"  {sec}: {section_counts[sec]} students")
        
        print("="*60 + "\n")


if __name__ == "__main__":
    print("="*60)
    print("CLASS/SECTION POPULATION SCRIPT")
    print("="*60)
    
    # Show current distribution
    show_current_distribution()
    
    print("\nOptions:")
    print("1. Interactive mode (assign one by one)")
    print("2. Batch mode (use predefined mapping)")
    print("3. Show distribution only")
    print("4. Exit")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    if choice == "1":
        populate_class_sections_interactive()
    elif choice == "2":
        print("\nBatch mode example:")
        print("Edit this script and define your mapping dictionary.")
        print("\nExample:")
        print("mapping = {")
        print("    'John Doe': {'class': '10th', 'section': 'A'},")
        print("    'Jane Smith': {'class': '10th', 'section': 'B'},")
        print("}")
        print("\nThen call: populate_class_sections_batch(mapping)")
    elif choice == "3":
        print("Distribution displayed above.")
    else:
        print("Exiting...")
    
    # Show final distribution
    if choice in ["1", "2"]:
        show_current_distribution()
