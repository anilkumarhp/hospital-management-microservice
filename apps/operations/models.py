import uuid
from django.db import models
from django.contrib.auth.models import User


class Organization(models.Model):
    # enum for'type' fields.
    class OrganizationType(models.TextChoices):
        CLINIC = 'CLINIC', 'Clinic'
        HOSPITAL = 'HOSPITAL', 'Hospital'

    # use UUIDs for primary key.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=265)
    type = models.CharField(
        max_length=10,
        choices=OrganizationType.choices,
        default=OrganizationType.CLINIC,
        db_index=True
    )

    # track when records are created or changed.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# THE PHYSICAL LOCATION
class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="branches")
    name = models.CharField(max_length=255)
    address_line_1 = models.CharField(max_length=255)
    city = models.CharField(max_length=100, db_index=True)
    locality = models.CharField(max_length=100, db_index=True)
    state = models.CharField(max_length=100)
        
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_branch_name_for_organization')
        ]
        ordering = ['organization', 'name']

    def __str__(self):
        return f"{self.organization.name} - {self.name}"
    
# 
class PhoneNumber(models.Model):
    class NumberType(models.TextChoices):
        RECEPTION = 'RECEPTION', 'Reception'
        EMERGENCY = 'EMERGENCY', 'Emergency'
        AMBULANCE = 'AMBULANCE', 'Ambulance'
        PHARMACY = 'PHARMACY', 'Pharmacy'
        FAX = 'FAX', 'Fax'
        OTHER = 'OTHER', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link back to the branch it belongs to
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="phone_numbers")
    
    number_type = models.CharField(max_length=20, choices=NumberType.choices, default=NumberType.RECEPTION, db_index=True)
    number = models.CharField(max_length=20) # We can add validators here later

    class Meta:
        # A branch can't have the same number listed twice.
        constraints = [
            models.UniqueConstraint(fields=['branch', 'number'], name='unique_number_for_branch')
        ]

    def __str__(self):
        return f"{self.get_number_type_display()}: {self.number}"


class UserProfile(models.Model):
    # This creates a one-to-one relationship with the default User model.
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    
    # The crucial link to the tenant. Every user belongs to one organization.
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    
    # We can add roles later, e.g., ('ADMIN', 'DOCTOR', 'RECEPTIONIST')
    # role = models.CharField(...)

    def __str__(self):
        return self.user.username
    

class UserProfile(models.Model):
    # ★-- ADD THIS NESTED CLASS --★
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DOCTOR = 'DOCTOR', 'Doctor'
        RECEPTIONIST = 'RECEPTIONIST', 'Receptionist'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    
    # ★-- ADD THIS FIELD --★
    role = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.DOCTOR # A sensible default for new users
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    

class UserInvite(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="invites")
    role = models.CharField(max_length=20, choices=UserProfile.Roles.choices)

    # The unique token that will be sent in the invitation email
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_accepted = models.BooleanField(default=False)
    
    # We can use this to make invites expire after a certain time
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # An organization can only have one pending invite for a given email address.
        constraints = [
            models.UniqueConstraint(fields=['organization', 'email'], name='unique_invite_for_organization')
        ]

    def __str__(self):
        return f"Invite for {self.email} to {self.organization.name}"
    
    
class StaffAvailability(models.Model):
    """
    Defines the regular weekly working hours for a staff member at a specific branch.
    e.g., Dr. Carter works at Downtown Branch on Mondays from 9 AM to 5 PM.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # We link to the UserProfile instead of User directly to easily access org and role
    staff_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="availability_schedules")
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="staff_schedules")
    
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ['staff_profile', 'day_of_week', 'start_time']
        constraints = [
            # A staff member can't have overlapping schedules at the same branch on the same day.
            models.UniqueConstraint(fields=['staff_profile', 'branch', 'day_of_week'], name='unique_schedule_per_staff_branch_day')
        ]

    def __str__(self):
        return f"{self.staff_profile.user.username} at {self.branch.name} on {self.get_day_of_week_display()}"


class LeaveRequest(models.Model):
    """
    Stores approved time-off requests for staff, which override their regular schedule.
    """
    class LeaveStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="leave_requests")
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=LeaveStatus.choices, default=LeaveStatus.PENDING, db_index=True)
    
    # Who approved or rejected this request
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_leave_requests")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        return f"Leave for {self.staff_profile.user.username} from {self.start_datetime} to {self.end_datetime}"


class Bed(models.Model):
    """Represents a single bed within a hospital branch."""
    class BedStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    class BedCategory(models.TextChoices):
        GENERAL_WARD = 'GENERAL_WARD', 'General Ward'
        SEMI_PRIVATE = 'SEMI_PRIVATE', 'Semi-Private Room'
        PRIVATE_ROOM = 'PRIVATE_ROOM', 'Private Room'
        ICU = 'ICU', 'Intensive Care Unit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="beds")
    
    number = models.CharField(max_length=20)
    category = models.CharField(max_length=20, choices=BedCategory.choices)
    status = models.CharField(max_length=20, choices=BedStatus.choices, default=BedStatus.AVAILABLE, db_index=True)
    daily_charge = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['branch', 'number'], name='unique_bed_number_per_branch')
        ]
    
    def __str__(self):
        return f"Bed {self.number} ({self.category}) at {self.branch.name}"
    

class Bed(models.Model):
    """Represents a single bed within a hospital branch."""
    class BedStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'

    class BedCategory(models.TextChoices):
        GENERAL_WARD = 'GENERAL_WARD', 'General Ward'
        SEMI_PRIVATE = 'SEMI_PRIVATE', 'Semi-Private Room'
        PRIVATE_ROOM = 'PRIVATE_ROOM', 'Private Room'
        ICU = 'ICU', 'Intensive Care Unit'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name="beds")
    
    # ★-- NEW DETAILED LOCATION FIELDS --★
    building = models.CharField(max_length=100, blank=True, help_text="e.g., Main Building, Wing A")
    floor_number = models.IntegerField(null=True, blank=True)
    block_number = models.CharField(max_length=50, blank=True, help_text="e.g., Block C")
    number = models.CharField(max_length=20, help_text="The bed number or name, e.g., '101-A'")
    
    category = models.CharField(max_length=20, choices=BedCategory.choices)
    status = models.CharField(max_length=20, choices=BedStatus.choices, default=BedStatus.AVAILABLE, db_index=True)
    daily_charge = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        # ★-- UPDATED CONSTRAINT FOR TRUE UNIQUENESS --★
        constraints = [
            models.UniqueConstraint(
                fields=['branch', 'building', 'floor_number', 'block_number', 'number'], 
                name='unique_bed_location_in_branch'
            )
        ]
    
    def __str__(self):
        return f"Bed {self.number} ({self.category}) at {self.branch.name}"