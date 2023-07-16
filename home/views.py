import asyncio
from django.shortcuts import render, redirect
from django.http import HttpResponse

from .utils import *
import time
import random



def home(request):
    context = {
        "page" : "CodeChaser | Home"
    }
    return render(request, "home/index.html", context=context)

def career(request):
    career_data = GetCompaniesDetails()
    context = {
        "career" : career_data,
        "page" : "CodeChaser | Career"
    }
    return render(request, "home/career.html", context=context)

def upcommingContests(request, oj_name):
    context = {
        "page" : f"CodeChaser | {oj_name} Upcomming Contests", 
        "oj": oj_name, 
        "contestList": getUpcommingContests(oj_name)
    }
    return render(request, "home/upcommingContests.html", context=context)

def recommended_problmes(request):
    # Update User handle
    if handle_updated := request.GET.get('handle'):
        request.session['handle'] = handle_updated
        request.session['last_profile_update'] = 0
    
    # Update CF User profile for handle in session
    if handle := request.session.get('handle', None):
        current_time = int(time.time())
        time_difference = current_time - request.session.get('last_profile_update', 0)

        if time_difference > 86400:
            request.session['user'] = update_user_profile(handle)
            request.session['last_profile_update'] = current_time

    # Update problemset in DB with Celery background task
    update_problemset()#.delay() # commenting out as deploing background worker is paid

    # Codeforces user profile
    user = request.session.get('user', None)
    
    # Update user submission in DB with Celery background task
    if user:
        update_submissions(handle)#.delay(handle) # commenting out as deploing background worker is paid
    
    # Recent solve data
    recent_solves = get_recent_solves(handle)
    
    # Todays Date
    todays_date = datetime.datetime.now().strftime("%d %B %Y")
    
    # All recommended problems
    recommended_problems = get_recommended_problems(handle)
    
    # Todays recommended problems    
    todays_recommended_problems = recommended_problems[0] if len(recommended_problems) > 0 and recommended_problems[0][2] == todays_date  else None
    
    if todays_recommended_problems:
        recommended_problems.pop(0)
    
    context = {
        "page" : "CodeChaser | Recommended Problmes",
        "user" : user,
        'recent_solves' : recent_solves,
        'todays_date' : todays_date,
        'todays_recommended_problems' : todays_recommended_problems,
        'recommended_problems' : recommended_problems
    }
    return render(request, "home/recommended_problmes.html", context=context)

def generate_recommended_problmes(request):
    # CF user profile
    if user:= request.session.get('user', None):
        # Todays Date
        todays_date = datetime.datetime.now().strftime("%d %B %Y")
        
        # All recommended problems
        recommended_problems = get_recommended_problems(user.get('handle'))
        # Todays recommended problems    
        todays_recommended_problems = recommended_problems[0] if len(recommended_problems) > 0 and recommended_problems[0][2] == todays_date  else None
        
        # Generate Recommended Problems
        if todays_recommended_problems:
            if todays_recommended_problems[1] >= 60:
                genarate_recommend_problems(user.get('handle'), user.get('current_rating'), 3)
            else:
                print("Solve more Get more")
        else:
            genarate_recommend_problems(user.get('handle'), user.get('current_rating'), 10)
        
    return redirect('recommended_problmes')


