from myapp.models import CustomUser, Invitation
from myapp.tasks import send_invitation_email_task
import random
import string


def validate(email, inviter_user: CustomUser):
    """
    Validate the invitation email and inviter user.

    Args:
        email (str): The email of the user to invite.
        inviter_user (CustomUser): The user sending the invitation.

    Raises:
        ValueError: If the inviter is inviting themselves or if the email belongs to an existing user who is a member of a company.
    """
    if email.lower() == inviter_user.email.lower():
        raise ValueError({"error": "You cannot invite yourself."})
    # Prevent inviting an existing user who already belongs to a company
    if CustomUser.objects.filter(email=email, company__isnull=False).exists():
        raise ValueError({"error": "The user is already a member of a company."})

def send_invitation(email, first_name, last_name, inviter_user, inviter_company):
    """
      Sends an invitation to a user to join a company.

      Args:
          email (str): The email address of the invitee.
          first_name (str): The first name of the invitee.
          last_name (str): The last name of the invitee.
          inviter_user (CustomUser): The user sending the invitation.
          inviter_company (Company): The company the invitee is being invited to.

      Returns:
          Invitation: The created or existing invitation object.
    """
    user = inviter_user  # The user sending the invitation
    company = inviter_company # Pass the company from the view

    validate(email, user)

    # Check if the user has already been invited to this company
    existing_invitation = Invitation.objects.filter(email=email, company=company).first()
    if existing_invitation:
        # Send a reminder email asynchronously
        send_invitation_email_task.delay_on_commit(
            invite_code=existing_invitation.invite_code,
            company_name=company.name,
            inviter_name=user.username,
            to_email=email
        )
        return existing_invitation

    # Generate a 6-digit numeric code
    invite_code = generate_digit_code()
    # Send the invitation email asynchronously
    send_invitation_email_task.delay_on_commit(
        invite_code=invite_code,
        company_name=company.name,
        inviter_name=user.username,
        to_email=email
    )

    # Create the invitation
    invitation = Invitation.objects.create(
        email=email,
        first_name=first_name,
        last_name=last_name,
        company=company,
        invite_code=invite_code,
        invited_by=inviter_user
    )

    return invitation

def send_invitation_in_bulk(invited_persons, inviter_user, inviter_company):
    """
    Send invitations to multiple users in bulk.

    Args:
        invited_persons (list): A list of dictionaries containing email, first_name, and last_name of the invitees.
        inviter_user (CustomUser): The user sending the invitations.
        inviter_company (Company): The company the invitees are being invited to.

    Returns:
        list: A list of Invitation objects created.
    """
    invitations = []

    for person in invited_persons:
        email = person.get('email')
        first_name = person.get('first_name')
        last_name = person.get('last_name')
        invitation = send_invitation(email, first_name, last_name, inviter_user, inviter_company)
        invitations.append(invitation)
    return invitations

def validate_persons(invited_persons):
    """
    Validate the list of invited persons.

    Args:
        invited_persons (list): A list of dictionaries containing email, first_name, and last_name of the invitees.

    Raises:
        ValueError: If any of the invited persons have missing or invalid data.
    """
    for person in invited_persons:
        email = person.get('email')
        first_name = person.get('first_name')
        last_name = person.get('last_name')
        if not email or not first_name or not last_name:
            raise ValueError({"error": "All fields (email, first_name, last_name) are required."})

def generate_digit_code():
    # Generate a 6-digit numeric code
    return ''.join(random.choices(string.digits, k=6))