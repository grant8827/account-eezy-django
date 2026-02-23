import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'accounteezy.settings')
django.setup()

from django.contrib.auth import get_user_model
from businesses.models import Business
from django.db.models import Count

User = get_user_model()

def find_users_with_multiple_businesses():
    """
    Finds users who own more than one business by querying the Business model.
    """
    owners_with_multiple_businesses = Business.objects.values('owner') \
        .annotate(num_businesses=Count('id')) \
        .filter(num_businesses__gt=1)

    if not owners_with_multiple_businesses.exists():
        print("No users with multiple businesses found.")
        return

    print("Users with multiple businesses:")
    for owner_data in owners_with_multiple_businesses:
        owner_id = owner_data['owner']
        num_businesses = owner_data['num_businesses']
        try:
            user = User.objects.get(id=owner_id)
            print(f"  - User: {user.email} (ID: {user.id}) has {num_businesses} businesses.")
            businesses = Business.objects.filter(owner=user)
            for business in businesses:
                print(f"    - Business: {business.business_name} (ID: {business.id})")
        except User.DoesNotExist:
            print(f"  - User with ID: {owner_id} not found, but has {num_businesses} businesses.")


if __name__ == "__main__":
    find_users_with_multiple_businesses()
