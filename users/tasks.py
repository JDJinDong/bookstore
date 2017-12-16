from __future__ import absolute_import,unicode_literals
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

@shared_task
def send_active_email(token,username,email):
	#发送邮件
	subject = '书城用户激活' #标题
	message='感谢您的使用'
	sender = settings.EMAIL_FROM # 发件人
	receiver = [email] #收件人列表
	html_message = '<a href="http://127.0.0.1:8000/users/active/%s/">http://127.0.0.1:8000/users/avtive/</a>'%token
	send_mail(subject,message,sender,receiver,html_message=html_message)





