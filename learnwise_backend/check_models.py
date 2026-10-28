import os
os.environ["DJANGO_SETTINGS_MODULE"] = "learnwise_backend.settings"
import django
django.setup()
from accounts.models import User

f = User._meta.get_field('role')
print(f"role field: null={f.null}, blank={f.blank}, default={f.default}")
print(f"role choices: {f.choices}")
print()

# Also check if there are any users with role=None
users_with_null_role = User.objects.filter(role__isnull=True)
print(f"Users with null role: {users_with_null_role.count()}")
for u in users_with_null_role[:5]:
    print(f"  {u.email} - role: {u.role}")