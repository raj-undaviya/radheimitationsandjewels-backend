from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_appointment_email(to_email, subject, html_content):
    email = EmailMultiAlternatives(
        subject=subject,
        body='',
        from_email=settings.EMAIL_HOST_USER,
        to=[to_email]
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)