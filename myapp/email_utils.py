from django.core.mail import send_mail, BadHeaderError
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_invitation_email(invite_code, company_name, inviter_name, to_email):
    subject = "You're Invited to Join Our Company"
    html_message = render_to_string('invitation_email.html', {
        'invite_code': invite_code,
        'company_name': company_name,
        'inviter_name': inviter_name,
    })
    plain_message = strip_tags(html_message)
    from_email = settings.DEFAULT_FROM_EMAIL
    
    try:
        send_mail(subject, plain_message, from_email, [to_email], html_message=html_message)
    except TimeoutError:
        logger.error(f"TimeoutError while sending email to {to_email}.")
        return False
    except BadHeaderError:
        logger.error(f"BadHeaderError while sending email to {to_email}.")
        return False
    except Exception as e:
        logger.error(f"An error occurred while sending email to {to_email}: {e}")
        return False
    
    return True