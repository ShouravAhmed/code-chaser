from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name="home"),
    path('career/', career, name="career"),
    path('contests/<str:oj_name>/', upcommingContests, name="upcommingContests"),
    path('RecommendedProblems/', recommended_problmes, name="recommended_problmes"),
    path('GenerateRecommendedProblems/', generate_recommended_problmes, name="generate_recommended_problmes"),
]

    