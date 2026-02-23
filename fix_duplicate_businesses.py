
import os
import django
from django.db.models import Count, Max

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accounteezy.settings')
django.setup()

from django.contrib.auth import get_user_model
from businesses.models import Business

User = get_user_model()

def fix_users_with_multiple_businesses():
    """
    Finds users who own more than one business and deletes all but the most recently created one.
    """
    # First, revert the model to the original state to run the script
    # In businesses/models.py, change OneToOneField back to ForeignKey
    # and related_name back to 'owned_businesses'

    owners_with_multiple_businesses = Business.objects.values('owner_id') \
        .annotate(num_businesses=Count('id')) \
        .filter(num_businesses__gt=1)

    if not owners_with_multiple_businesses.exists():
        print("No users with multiple businesses found.")
        return

    print("The following businesses will be deleted:")
    businesses_to_delete = []

    for owner_data in owners_with_multiple_businesses:
        owner_id = owner_data['owner_id']
        
        # Get all businesses for this owner
        user_businesses = Business.objects.filter(owner_id=owner_id)
        
        # Find the most recent business
        most_recent_business = user_businesses.latest('created_at')
        
        print(f"User with ID {owner_id} has multiple businesses. Keeping the most recent one: '{most_recent_business.business_name}' (ID: {most_recent_business.id})")
        
        # Add all other businesses to the deletion list
        for business in user_businesses:
            if business.id != most_recent_business.id:
                print(f"  - Deleting '{business.business_name}' (ID: {business.id})")
                businesses_to_delete.append(business)

    if not businesses_to_delete:
        print("\nNo businesses need to be deleted.")
        return

    # Now, actually delete them
    for business in businesses_to_delete:
        business.delete()
    
    print(f"\nSuccessfully deleted {len(businesses_to_delete)} businesses.")

if __name__ == "__main__":
    fix_users_with_multiple_businesses()
