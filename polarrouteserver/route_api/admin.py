from django.contrib import admin

from .models import Route, Mesh, Job

admin.site.register(Route)
admin.site.register(Mesh)
admin.site.register(Job)
