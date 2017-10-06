from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^keyword/', views.keyword, name='keyword'),
    url(r'^project/', views.projectSpecific, name='projectSpecific'),
    url(r'^projects/', views.projects, name='projects'),
    url(r'^create_project/', views.create_project, name='create_project'),
    url(r'^savefile/', views.saveFile, name='saveFile'),
    url(r'^start_explore/', views.start_explore, name='start_explore'),
    url(r'^explore_collect/', views.explore_collect, name='explore_collect'),
    url(r'^explore_collect_keyword/', views.explore_collect_keyword, name='explore_collect_keyword'),
    url(r'^$', views.index, name='index'),
]