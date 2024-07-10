from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

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
    



def generate_and_send_otp(email):
    otp = get_random_string(length=6, allowed_chars='0123456789')
    send_mail(
        'Your OTP Code',
        f'Your OTP code is {otp}',
        'from@example.com',
        [email],
        fail_silently=False,
    )
    return otp
 