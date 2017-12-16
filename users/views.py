from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
import re
from django_redis import get_redis_connection
from books.models import Books
from users.models import Passport, Address
from django.http import HttpResponse, JsonResponse
from utils.decorators import login_required
from order.models import OrderInfo, OrderGoods
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
from users.tasks import send_active_email
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
# Create your views here.
def register(request):
	return render(request,'users/register.html')

def register_handle(request):
	#进行用户注册处理
	#接收数据
	# data = json.loads(request.body.decode('utf-8'))
	username = request.POST.get('user_name')
	password = request.POST.get('pwd')
	email = request.POST.get('email')

	#进行数据校验
	if not all([username,password,email]):
		#有数据为空
		return render(request,'users/register.html',{'errmsg':'参数不能为空'})
	#判断邮箱是否合法
	if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
		#邮箱不合法
		return render(request,'users/register.html',{'errmsg':'邮箱格式输入不合法'})

	p = Passport.objects.check_passport(username=username)
	if p:
		return render(request,'users/register.html',{'errmsg':'用户名存在'})

	#进行业务处理：注册，向账户系统添加账户，写入到数据库
	passport = Passport.objects.add_one_passport(username=username,password=password,email=email)
	# passport.save()

	#生成激活的token itsdangerous
	serializer = Serializer(settings.SECRET_KEY,3600)
	token = serializer.dumps({'confirm':passport.id}) #返回bytes
	token = token.decode()

	#给用户的邮箱发激活邮件
	send_mail('书城用户激活','',settings.EMAIL_FROM,[email],html_message='<a href="http://127.0.0.1:8000/users/active/%s">http://127.0.0.1:8000/users/active/</a>'%token)
	# send_active_email.delay(token,username,email)
	return redirect(reverse('users:login'))

def login(request):
	username = '',
	checked = ''
	context = {
		'username':username,
		'checked':checked,
	}
	return render(request,'users/login.html',context)

def logout(request):
	#清空用户的session信息
	request.session.flush()
	#跳转到首页
	return redirect(reverse('books:index'))

def login_handle(request):
	#获取数据
	username = request.POST.get('username')
	password = request.POST.get('password')
	remember = request.POST.get('remember')
	verifycode = request.POST.get('verifycode')
	print(username,password,remember,verifycode)

	#数据校验
	if not all([username,password,remember,verifycode]):
		#有数据为空
		return JsonResponse({'res':2})

	if verifycode.upper() != request.session['verifycode']:
		return JsonResponse({'res':2})

	#进行处理：根据用户名和密码找账户信息
	passport = Passport.objects.get_one_passport(username=username,password=password)
	if passport:
		#用户名密码正确
		#获取session中的url_path
		next_url = reverse('books:index')
		jres = JsonResponse({'res':1,'next_url':next_url})
		#判断用户是否需要记住用户名
		if remember == 'true':
			jres.set_cookie('username',username,max_age=7*24*3600)
		else:
			#不要记住用户名
			jres.delete_cookie('username')
		#记住用户的登录状态
		request.session['islogin'] = True
		request.session['username'] = username
		request.session['passport_id'] = passport.id

		return jres

	else:
		return JsonResponse({'res':0})

@login_required
def user(request):
	#用户中心－信息页
	passport_id = request.session.get('passport_id')
	#获取用户的基本信息
	addr = Address.objects.get_default_address(passport_id=passport_id)
	#获取用户的最近浏览信息
	con = get_redis_connection('default')
	key = 'history_%d'%passport_id
	#取出用户最近浏览的5个商品的id
	history_li = con.lrange(key,0,4)
	books_li = []
	for id in history_li:
		books = Books.objects.get_books_by_id(books_id=id)
		books_li.append(books)
	return render(request,'users/user_center_info.html',{'addr':addr,'page':'user','books_li':books_li})

@login_required
def address(request):
	#用户中心－地址页
	#获取登录用户的id
	passport_id = request.session.get('passport_id')
	if request.method == 'GET':
		#显示地址页面
		#查询用户的默认地址
		addr = Address.objects.get_default_address(passport_id=passport_id)
		return render(request,'users/user_center_site.html',{'addr':addr,'page':'address'})
	else:
		#添加收货地址
		#接收数据
		recipient_name = request.POST.get('username')
		recipient_addr = request.POST.get('addr')
		zip_code = request.POST.get('zip_code')
		recipient_phone = request.POST.get('phone')

	#进行校验
	if not all([recipient_name,recipient_addr,zip_code,recipient_phone]):
		return render(request,'users/user_center_site.html',{'errmag':'参数不必为空'})

	#添加收货地址
	Address.objects.add_one_address(
		passport_id = passport_id,
		recipient_name = recipient_name,
		recipient_addr = recipient_addr,
		zip_code = zip_code,
		recipient_phone = recipient_phone
	)
	return redirect(reverse('users:address'))

@login_required
def order(request):
	#用户中心－订单页
	#查询用户的订单信息
	passport_id = request.session.get('passport_id')
	#获取订单信息
	order_li = OrderInfo.objects.filter(passport_id=passport_id)
	#遍历获取订单的商品信息
	#order->OrderInfo实例对象
	for order in order_li:
		#根据订单id查询订单商品信息
		order_id = order.order_id
		order_books_li = OrderGoods.objects.filter(order_id=order_id)

		#计算商品的小计
		#order_books ->OrderBooks实例对象
		for order_books in order_books_li:
			count = order_books.count
			price = order_books.price
			amount = count * price
			#保存订单中每一个商品的小计
			order_books.amount  = amount
		#给order对象动态增加一个属性order_goods_li,保存订单中商品的信息
		order.order_books_li = order_books_li

	context = {
		'order_li':order_li,
		'page':'order'
	}
	return render(request,'users/user_center_order.html',context)

def verifycode(request):
	#引入绘图模块
	from PIL import Image,ImageDraw,ImageFont
	#引入随机函数模块
	import random
	#定义变量，用户画面的背景色，宽，高
	bgcolor = (random.randrange(20,100),random.randrange(20,100),255)
	width = 100
	height = 25
	#创建画面对象
	im = Image.new('RGB',(width,height),bgcolor)
	#创建画笔对象
	draw = ImageDraw.Draw(im)
	#调用画笔的point()函数绘制噪点
	for i in range(0,100):
		xy = (random.randrange(0,width),random.randrange(0,height))
		fill = (random.randrange(0,255),255,random.randrange(0,255))
		draw.point(xy,fill=fill)
	#定义验证码的备选值
	str1 = 'ABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0'
	#随机选取4个值作为验证码
	rand_str = ''
	for i in range(0,4):
		rand_str += str1[random.randrange(0,len(str1))]
	#构造字体对象
	font = ImageFont.truetype('/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',15)
	#构造字体颜色
	fontcolor = (255,random.randrange(0,255),random.randrange(0,255))
	#绘制四个字
	draw.text((5,2),rand_str[0],font=font,fill=fontcolor)
	draw.text((25,2),rand_str[1],font=font,fill=fontcolor)
	draw.text((50,2),rand_str[2],font=font,fill=fontcolor)
	draw.text((75,2),rand_str[3],font=font,fill=fontcolor)
	#释放画笔
	del draw
	#存入session,用于做进一步验证
	request.session['verifycode'] = rand_str
	#内存文件操作
	import io
	buf = io.BytesIO()
	#将图片保存在内存中，文件类型为png
	im.save(buf,'png')
	#将内存中的图片数据返回给客户端，MIME类型为图片png
	return HttpResponse(buf.getvalue(),'image/png')

def register_active(request,token):
	#用户激活
	serializer = Serializer(settings.SECRET_KEY,3600)
	try:
		info = serializer.loads(token)
		passport_id = info['confirm']
		#用户激活
		passport = Passport.objects.get(id=passport_id)
		passport.is_active = True
		passport.save()
		#跳转的登录页
		return redirect(reverse('user:login'))
	except SignatureExpired:
		#链接过期
		return HttpResponse('激活链接已过期')

















