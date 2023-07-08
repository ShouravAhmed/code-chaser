from bs4 import BeautifulSoup
import datetime
import requests
import json

from .models import *
from django.db import transaction

from celery import shared_task

from itertools import groupby
from operator import attrgetter

import random


# =======================================================================

def GetCompaniesSalary():
    salary_url = "https://tahanima.github.io/2021/09/12/monetary-compensation-at-various-software-companies-of-bangladesh-for-an-entry-level-position/"
    salary_res = requests.get(salary_url)
    salary_bts = BeautifulSoup(salary_res.text, 'html.parser')

    all_companies = salary_bts.find("tbody").find_all("tr")
    software_company_details_bd = {}

    for company in all_companies:
        data = [x.text.strip() for x in company.find_all('td')]
        salary = [
            x.strip()
            for x in ((data[2].replace('Tk.', '')).replace(',', ''))
            .strip()
            .split(' ')
            if x not in ["", "-"]
        ]

        if data[0] in software_company_details_bd:
            software_company_details_bd[data[0]]['Positions'].append(
                {
                    'Position' : data[1],
                    'Salary' : {
                        'Low' : int(salary[0]),
                        'Hi' : int(salary[1])
                    }
                }
            )
        else:
            software_company_details_bd[data[0]] = {
                "Name" : data[0],
                "Positions" : [
                    {
                        'Position' : data[1],
                        'Salary' : {
                            'Low' : int(salary[0]),
                            'Hi' : int(salary[1])
                        }
                    }
                ]
            }
    return software_company_details_bd

def GetCompaniesProfile():
    company_profile_url = "https://tahanima.github.io/2022/04/01/profile-of-software-companies-of-bd/"
    company_profile_res = requests.get(company_profile_url)
    company_profile_bts = BeautifulSoup(company_profile_res.text, 'html.parser')

    all_companies_info = company_profile_bts.find("table").find_all("tr")
    company_profile = []

    for company in all_companies_info:
        data = company.find_all('td')
        if len(data) == 5:
            name = data[0].text.strip()
            website = data[1].find('a')['href']
            career_website = "".join([x['href'].strip() for x in data[2].find_all('a') if x['href'].strip() != ""])
            facebook = "".join([x['href'].strip() for x in data[3].find_all('a') if x['href'].strip() != ""])
            linkedin = "".join([x['href'].strip() for x in data[4].find_all('a') if x['href'].strip() != ""])
            company_profile.append({
                'Name' : name,
                'Website' : website,
                'Career' : career_website,
                'Facebook': facebook,
                'LinkedIn' : linkedin
            })
    return company_profile

def GetCompaniesDetails():
    try:
        software_company_details_bd = GetCompaniesSalary()
        company_profile = GetCompaniesProfile()
        software_company_details_bd = software_company_details_bd
        company_profile = company_profile

        for company in company_profile:
            name = ' '.join([x.strip().replace('.', '').lower() for x in company['Name'].split() if x.strip().replace('.', '').lower() != 'ltd'])
            matched_company = ""
            for company_name, data in software_company_details_bd.items():
                if name.replace('limited', '').strip() in ' '.join([x.strip() for x in company_name.lower().split('.') if x.strip() != ""]):
                    matched_company = company_name
            if matched_company == "":
                software_company_details_bd[company['Name']] = company
            else:
                software_company_details_bd[matched_company]['Website'] = company['Website']
                software_company_details_bd[matched_company]['Career'] = company['Career']
                software_company_details_bd[matched_company]['Facebook'] = company['Facebook']
                software_company_details_bd[matched_company]['LinkedIn'] = company['LinkedIn']

        companies_info =  {
            'Response' : 'ok',
            'Companies' : software_company_details_bd
        }
        career_data = []

        if "Companies" in companies_info:
            for Name, data in companies_info["Companies"].items():
                company = {
                    "Name": Name,
                    "Website": data["Website"]
                    if "Website" in data and data["Website"] != ""
                    else "Unknown",
                    "CareerPage": data["Career"]
                    if "Career" in data and data["Career"] != ""
                    else "Unknown",
                    "Facebook": data["Facebook"]
                    if "Facebook" in data and data["Facebook"] != ""
                    else "Unknown",
                    "LinkedIn": data["LinkedIn"]
                    if "LinkedIn" in data and data["LinkedIn"] != ""
                    else "Unknown",
                }

                if "Positions" in data:
                    for position in data["Positions"]:
                        company["Position"] = position["Position"]
                        if "Salary" in position:
                            company["Salary"] = [position["Salary"]["Low"], position["Salary"]["Hi"]]
                        else:
                            company["Salary"] = [0, 0]
                        career_data.append(company)
                else:
                    company["Position"] = "Unknown"
                    company["Salary"] = [0, 0]
                    career_data.append(company)                                            

        return sorted(career_data, key=lambda x: x["Salary"][0], reverse=True)
    except Exception:
        return {
            "Response" : "error"
        }

# =======================================================================

class GetJSON:
    def __init__(self):
        self.hdr = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
        self.session = requests.Session()
        self.json = None
    def fetch(self, url):
        try:
            with self.session.get(url, headers = self.hdr) as responce:
                self.json = responce.json()
        except Exception as e:
            print("Exception:", e)

# =======================================================================

def getUpcommingContests(name):
    apiLinks = {
        "all": "https://kontests.net/api/v1/all",
        "topcoder": "https://kontests.net/api/v1/top_coder",
        "atcoder": "https://kontests.net/api/v1/at_coder",
        "codechef": "https://kontests.net/api/v1/code_chef",
        "leetcode": "https://kontests.net/api/v1/leet_code",
        "codeforces": "https://kontests.net/api/v1/codeforces",
        "cfgym": "https://kontests.net/api/v1/codeforces_gym"
    }

    contestList = []
    onlineJudges = []
    data = GetJSON()

    try:
        if name == 'CF':
            data.fetch(apiLinks["codeforces"])
            onlineJudges.append(data.json)
            data.fetch(apiLinks["cfgym"])
            onlineJudges.append(data.json)   
        elif name == "TC":
            data.fetch(apiLinks["topcoder"])
            onlineJudges.append(data.json)
        elif name == "CC":
            data.fetch(apiLinks["codechef"])
            onlineJudges.append(data.json)
        elif name == "AT":
            data.fetch(apiLinks["atcoder"])
            onlineJudges.append(data.json)
        elif name == "LE":
            data.fetch(apiLinks["leetcode"])
            onlineJudges.append(data.json)
        else:
            data.fetch(apiLinks["all"])
            onlineJudges.append(data.json)

    except Exception as e:
        print("Exception:", e)    

    for onlineJudge in onlineJudges:
        tmpData = []
        for contest in onlineJudge:
            # timezone = 6
            # try:
            #     timezone = int(str(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo))
            # except Exception as e:
            #     print("Exception:", e)

            contest_date_time = " ".join(contest["start_time"].split('T')).replace('Z', ' ')
            contest_date_time = ' '.join(contest_date_time.split(' ')[:2])
            contest_date_time = contest_date_time.split('.')[0]

            contest_date_time = datetime.datetime.strptime(contest_date_time, '%Y-%m-%d %H:%M:%S')
            contest_date_time = contest_date_time + datetime.timedelta(hours=6)
            # contest_date_time = contest_date_time.strftime("%d %B %Y - %I:%M %p")

            current_time = datetime.datetime.now()
            time_left = contest_date_time - current_time

            days = time_left.days
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            time_left_str = f"{days} days, {hours} hours, {minutes} minutes"

            contest = {
                "Name" : contest["name"] ,  
                "Time" : contest_date_time, 
                "URL" : contest["url"],
                "TimeLeft" : time_left_str
            }
            if "site" in contest:
                contest["OJ"] = "site"  
            elif name == "CF":
                contest["OJ"] = "CodeForces"
            elif name == "CC":
                contest["OJ"] = "CodeChef"
            elif name == "TC":
                contest["OJ"] = "TopCoder"
            elif name == "AT":
                contest["OJ"] = "AtCoder"
            elif name == "LE":
                contest["OJ"] = "LeetCode"
            tmpData.append(contest)
            
        tmpData = sorted(tmpData, key=lambda x: x["Time"])
        contestList.extend(iter(tmpData))
        
    return contestList

# =======================================================================
# =======================================================================

def update_user_profile(handle):
    try:
        data = GetJSON()
        data.fetch(f'https://codeforces.com/api/user.info?handles={handle}')
        
        profile = data.json
        if profile['status'] != 'OK':
            return None
        
        profile = profile['result'][0]
        
        return {
            'handle':handle,
            'max_rank' : profile['maxRank'],
            'max_rating' : profile['maxRating'],
            'current_rank' : profile['rank'],
            'current_rating' : profile['rating'],
            'profile_picture' : profile['titlePhoto']
        }
    
    except Exception as e:
        print("update_user_profile EXCEPTION: " , e)
    
    return None

# =======================================================================

@shared_task
def update_submissions(handle):
    update, _ = Update.objects.get_or_create(name=f'submission_update_{handle}')

    update_time = update.epoch_time
    update_time = datetime.datetime.fromtimestamp(update_time)

    current_time = datetime.datetime.now()
    time_difference = current_time - update_time

    print(f"{handle}'s : Submission Update time:", update_time)
    print(f"{handle}'s : Submission Current time:", current_time)

    if time_difference > datetime.timedelta(minutes=5):
        Update.objects.filter(name=f'problemset_update_{handle}').update(epoch_time=int(current_time.timestamp()))

        try:
            data = GetJSON()
            data.fetch(f'https://codeforces.com/api/user.status?handle={handle}')
            
            submissions = data.json
            if submissions['status'] != 'OK':
                return
             
            submissions = submissions['result']
            submission_fatched = 0
            
            just_updated = set()
            
            with transaction.atomic():
                for submission in submissions:
                    
                    try:
                        if 'verdict' in submission and submission['verdict'] == 'OK':    
                            problem_id = str(submission['problem']['contestId']) + '.' + submission['problem']['index']
                            
                            if problem_id not in just_updated:
                                just_updated.add(problem_id)
                                
                                problem = Problem.objects.filter(problem_id=problem_id)
                                if problem.exists():
                                    problem = problem[0]
                                    
                                    if not Submission.objects.filter(handle=handle, problem=problem).exists():
                                        Submission.objects.create(
                                            handle=handle, 
                                            problem=problem,
                                            submission_time=submission['creationTimeSeconds']
                                        )
                                    else:
                                        Submission.objects.filter(
                                            handle=handle, 
                                            problem=problem
                                        ).update(submission_time=submission['creationTimeSeconds'])
                                    
                                    submission_fatched += 1
                                    if submission_fatched % 10 == 0:
                                        print(f'{submission_fatched} submission fetched for user: {handle}')
                    
                    except Exception as e:
                        print("update_submission processing exception:", e)    
                        
            transaction.commit()            
        
        except Exception as e:
            print("update_submission EXCEPTION:", e)   
            return None    

# =======================================================================

def get_recent_solves(handle):
    start_date = datetime.datetime.now() - datetime.timedelta(days=30)
    start_date = int(start_date.timestamp())
    submissions = Submission.objects.filter(handle=handle, submission_time__gte=start_date)
    
    rating_categories = { 1300: 'A', 1500: 'B', 1700: 'C', 1900: 'D', 2100: 'E', 2500: 'F' }
    category_frequency = {}
    
    for submission in submissions:
        category = 'G'
        
        for rating, cat in rating_categories.items():
            if submission.problem.rating <= rating:
                category = cat
                break
    
        category_frequency[category] = category_frequency.get(category, 0) + 1
    return category_frequency
    
def get_recommended_problems(handle):
    all_recommended_problems = RecommendedProblem.objects.filter(handle=handle)
    solved_problem_ids = set(Submission.objects.filter(handle=handle).values_list('problem__problem_id', flat=True))
    grouped_problems_by_date = groupby(reversed(sorted(all_recommended_problems, key=attrgetter('date'))), key=attrgetter('date'))

    formatted_problems = []
    for date, recommended_problems in grouped_problems_by_date:
        problem_list = list(recommended_problems)
        problem_list = [[recommended_problem, 'solved' if recommended_problem.problem.problem_id in solved_problem_ids else 'unsolved', f'https://codeforces.com/contest/{recommended_problem.problem.problem_id.split(".")[0]}/problem/{recommended_problem.problem.problem_id.split(".")[1]}'] for recommended_problem in problem_list]
        solve_percentage = int((sum(1 for problem, status, url in problem_list if status == 'solved') / len(problem_list)) * 100)
        formatted_problems.append([problem_list, solve_percentage, datetime.datetime.fromtimestamp(date).strftime("%d %B %Y")])

    return formatted_problems
    
def genarate_recommend_problems(handle, rating, problem_cnt):
    start_date = datetime.datetime.now() - datetime.timedelta(days=30)
    start_date = int(start_date.timestamp())
    submissions = Submission.objects.filter(handle=handle, submission_time__gte=start_date)

    recent_tags = {}
    for submission in submissions:
        for tag in submission.problem.tags.all():
            recent_tags[tag.name] = recent_tags.get(tag.name, 0) + 1
            
    total_tag_solved = sum(frq for tag, frq in recent_tags.items())
    
    rating = int((rating+50)/100) * 100
    
    recommended_problems = Problem.objects.exclude(submission__handle=handle).filter(rating__gte=rating+100, rating__lte=rating+300)
    
    recommended_problems_probability = []
    for problem in recommended_problems:
        tags = [tag.name for tag in problem.tags.all()]
        probability = (1.0 - (sum(recent_tags.get(tag, 0) for tag in tags) / total_tag_solved)) * int(problem.problem_id.split('.')[0])
        recommended_problems_probability.append((problem, probability))

    chosen_problems = random.choices(
        [q[0] for q in recommended_problems_probability],
        [q[1] for q in recommended_problems_probability],
        k=problem_cnt,
    )   
    
    current_time = datetime.datetime.now()
    current_time = datetime.datetime(current_time.year, current_time.month, current_time.day)
    
    with transaction.atomic():
        for problem in chosen_problems:
            RecommendedProblem.objects.create(
                handle=handle,
                problem=problem,
                date=int(current_time.timestamp())
            )
    transaction.commit()

# =======================================================================
# =======================================================================

@shared_task
def update_problemset():
    update, _ = Update.objects.get_or_create(name='problemset_update')

    update_time = update.epoch_time
    update_time = datetime.datetime.fromtimestamp(update_time)
    update_time = datetime.datetime(update_time.year, update_time.month, update_time.day)

    current_time = datetime.datetime.now()
    current_time = datetime.datetime(current_time.year, current_time.month, current_time.day)

    print("\nUpdate time:", update_time)
    print("Current time:", current_time)
    
    if update_time != current_time:
        Update.objects.filter(name='problemset_update').update(epoch_time=int(current_time.timestamp()))

        try:
            data = GetJSON()
            data.fetch('https://codeforces.com/api/problemset.problems')
            problemset = data.json['result']['problems']
            
            problem_fetched = 0
            with transaction.atomic():
                for problem_data in problemset:
                    try:
                        problem_id = str(problem_data['contestId']) + '.' + problem_data['index']
                        if not Problem.objects.filter(problem_id=problem_id).exists():
                            rating = problem_data['rating'] if 'rating' in problem_data else 0

                            problem = Problem.objects.create(
                                problem_id=problem_id, 
                                name=problem_data['name'],
                                rating=rating
                            )
                            for tag_name in problem_data['tags']:
                                tag, _ = Tag.objects.get_or_create(name=tag_name)
                                problem.tags.add(tag)

                            problem_fetched += 1
                            if problem_fetched % 10 == 0:
                                print(f'Total {problem_fetched} problem fetched')

                    except Exception as e:
                        print("Problem set processing exception:", e) 

            transaction.commit()     

        except Exception as e:
            print("Problem Set Fatching Exception:", e)
    
    