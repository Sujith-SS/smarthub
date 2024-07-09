from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(email, otp):
    subject = 'Your OTP for Verification'
    message = f'Your OTP is: {otp}'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    try:
        send_mail(subject, message, from_email, recipient_list)
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {str(e)}")
        return False