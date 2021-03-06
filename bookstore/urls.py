"""bookstore URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,include
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    # url(r'^users/',include('users.urls')),
    url(r'^users/',include('users.urls',namespace='users')),
    url(r'^books/', include('books.urls', namespace='books')),
    url(r'^tinymce/',include('tinymce.urls')),
    url(r'^cart/',include('cart.urls',namespace='cart')),
    url(r'^order/',include('order.urls',namespace='order')),
    url(r'^comment/',include('comments.urls',namespace='comment')),
    url(r'^search/',include('haystack.urls')), #搜索配置
]
