from django.contrib import admin
from books.models import Books

# Register your models here.

#在admin中添加有关商品的编辑功能
admin.site.register(Books)


