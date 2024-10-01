from celery import shared_task
from .email_utils import send_invitation_email

@shared_task
def send_invitation_email_task(invite_code, company_name, inviter_name, to_email):
    return send_invitation_email(invite_code, company_name, inviter_name, to_email)
