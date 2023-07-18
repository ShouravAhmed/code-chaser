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

import logging
logger = logging.getLogger(__name__)

from django.db.models import Sum, Count, Q, F, FloatField, Case, When
from django.db.models.functions import Cast, Substr


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
            logger.exception(f"GetJSON Exception: {e}")

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
        logger.exception(f"getUpcommingContests Exception: {e}")    

    for onlineJudge in onlineJudges:
        tmpData = []
        for contest in onlineJudge:
            contest_date_time = " ".join(contest["start_time"].split('T')).replace('Z', ' ')
            contest_date_time = ' '.join(contest_date_time.split(' ')[:2])
            contest_date_time = contest_date_time.split('.')[0]

            contest_date_time = datetime.datetime.strptime(contest_date_time, '%Y-%m-%d %H:%M:%S')
            contest_date_time = contest_date_time + datetime.timedelta(hours=6)
            
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
        logger.exception(f"update_user_profile EXCEPTION: {e}")
    
    return None

# ======================================================================= 
# =======================================================================

# @shared_task # commenting out as deploing background worker is paid
def update_submissions(handle):
    # Get the update information for the handle
    update, _ = Update.objects.get_or_create(name=f'submission_update_{handle}')

    # Convert the update time to datetime
    update_time = update.epoch_time
    update_time = datetime.datetime.fromtimestamp(update_time)

    # Get the current time and calculate the time difference
    current_time = datetime.datetime.now()
    time_difference = current_time - update_time

    # Check if the time difference is greater than 5 minutes
    if time_difference > datetime.timedelta(minutes=5):
        logger.info(f"{handle}'s Submission Updating | Time: {current_time}")
        try:
            # Fetch submissions data from the Codeforces API
            data = GetJSON()
            data.fetch(f'https://codeforces.com/api/user.status?handle={handle}')

            # Check if the submissions status is OK
            submissions = data.json
            if submissions['status'] != 'OK':
                logger.exception(f"{handle}'s Submission Status Not Ok")
                return

            # Get the submissions data
            submissions = submissions['result']

            # Fetch solved problems and all problems in bulk to optimize database queries
            solved_problems = {
                submission.problem.problem_id: submission
                for submission in Submission.objects.filter(handle=handle).prefetch_related('problem')
            }
            all_problems = {
                problem.problem_id: problem
                for problem in Problem.objects.all()
            }

            # Set to track just updated problem IDs
            just_updated = set()

            # Lists to store submissions for creation and update
            submissions_to_create = []
            submissions_to_update = []
            submissions_to_update_time = []
            
            with transaction.atomic():
                for submission in submissions:
                    try:
                        if 'verdict' in submission and submission['verdict'] == 'OK':
                            problem_id = str(submission['problem']['contestId']) + '.' + submission['problem']['index']

                            # Check if the problem has already been updated
                            if problem_id not in just_updated:
                                just_updated.add(problem_id)

                                # Check if the problem is already solved or needs to be created
                                if problem_id not in solved_problems:
                                    if problem_id in all_problems:
                                        # Create a new submission object
                                        submissions_to_create.append(
                                            Submission(
                                                handle=handle,
                                                problem=all_problems[problem_id],
                                                submission_time=submission['creationTimeSeconds']
                                            )
                                        )
                                elif solved_problems[problem_id].submission_time != submission['creationTimeSeconds']:
                                    # Update the submission time for an existing solved problem
                                    submissions_to_update.append(solved_problems[problem_id])
                                    submissions_to_update_time.append(submission['creationTimeSeconds'])

                    except Exception as e:
                        logger.exception(f"update_submission processing exception: {e}")

                    # Check if 100 submissions are ready for creation
                    if len(submissions_to_create) >= 100:
                        # Create the submissions in bulk
                        Submission.objects.bulk_create(submissions_to_create)
                        submissions_to_create.clear()
                        logger.info(f"100 Submissions Created for: {handle}")

                if submissions_to_create:
                    # Create the remaining submissions in bulk
                    Submission.objects.bulk_create(submissions_to_create)
                    logger.info(f"{len(submissions_to_create)} Submissions Created for: {handle}")

                if submissions_to_update:
                    # Create the case statements for updating submission times
                    case_statements = [
                        When(pk=submission_obj.pk, then=submission_time)
                        for submission_obj, submission_time in zip(submissions_to_update, submissions_to_update_time)
                    ]

                    # Update the submission times in bulk using case statements
                    Submission.objects.filter(
                        pk__in=[submission_obj.pk for submission_obj in submissions_to_update]
                    ).update(
                        submission_time=Case(*case_statements, default=F('submission_time'))
                    )
                    logger.info(f"{len(submissions_to_update)} Submissions Updated for: {handle}")
            transaction.commit()

            logger.info(f"All Submissions Saved for user: {handle}\n")
            Update.objects.filter(name=f'submission_update_{handle}').update(epoch_time=int(current_time.timestamp()))

        except Exception as e:
            logger.exception(f"update_submission EXCEPTION: {e}")
    else:
        logger.info(f"{handle}'s Submission Already Updated | Update Time: {update_time}\n")

# ======================================================================= 
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
    
    category_frequency = dict(sorted(category_frequency.items()))
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
    try:
        # Calculate the start date as 30 days ago
        start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        start_date = int(start_date.timestamp())

        # Get all submissions for the handle
        submissions = Submission.objects.filter(handle=handle)

        # Check if there are any submissions for the handle
        if not submissions.exists():
            logger.info(f'User {handle} does not have any submissions')
            return

        logger.info(f'Recommending problems for handle: {handle}')

        # Exclude submissions submitted before the start date
        submissions = submissions.exclude(submission_time__lt=start_date)

        # Calculate the frequency of recent tags
        recent_tags = {tag['problem__tags__name']: tag['frequency'] for tag in submissions.values('problem__tags__name').annotate(frequency=Count('problem__tags')).values('problem__tags__name', 'frequency')}

        # Calculate the total number of tags solved by the user
        total_tag_solved = sum(value for key, value in recent_tags.items()) or 1

        # Adjust the rating based on the user's rating
        rating = int((rating + 50) / 100) * 100

        # Get the recommended problems based on the adjusted rating
        recommended_problems = Problem.objects.exclude(submission__handle=handle).filter(
            rating__gte=rating + 100, 
            rating__lte=rating + 300
        ).prefetch_related('tags')

        logger.info(f'Problem recommendation in progress for handle: {handle}')

        # Calculate the probability for each recommended problem
        recommended_problems_probability = []
        for problem in recommended_problems:
            tags = [tag.name for tag in problem.tags.all()]
            if len(tags) > 0 and problem.rating > 0:
                probability = (1.0 - (sum(recent_tags.get(tag, 0) for tag in tags) / total_tag_solved)) * int(problem.problem_id.split('.')[0])
                recommended_problems_probability.append((problem, probability))

        logger.info(f'Probability calculated for problems | {handle}')

        # Calculate the rating levels
        rating_levels = [rating + 100, rating + 200, rating + 300]

        # Choose a specified number of problems randomly based on their probabilities
        chosen_problems = []
        problems_by_level = {level: [[problem, probability] for problem, probability in recommended_problems_probability if problem.rating == level] for level in rating_levels}
        
        if problem_cnt == 6:    
            for cnt, level in enumerate(rating_levels, start=1):
            
                level_problems = problems_by_level[level]
                chosen_problems.extend(
            
                    random.choices(
                        [p[0] for p in level_problems],
                        [p[1] for p in level_problems],
            
                        k=(3 if cnt == 1 else (2 if cnt == 2 else 1))
                    )
                )
        else:
            for cnt, level in enumerate(rating_levels[1:], start=1):
            
                level_problems = problems_by_level[level]
                chosen_problems.extend(
            
                    random.choices(
                        [p[0] for p in level_problems],
                        [p[1] for p in level_problems],
            
                        k=(1 if cnt == 1 else 2)
                    )
                )

        # Shuffle the chosen problems to ensure randomness
        random.shuffle(chosen_problems)

        # Get the current time and set it to the current day
        current_time = datetime.datetime.now()
        current_time = datetime.datetime(current_time.year, current_time.month, current_time.day)

        # Create the recommended problems to be stored in the database
        recommended_problems_to_create = [
            RecommendedProblem(
                handle=handle, 
                problem=problem,
                date=int(current_time.timestamp())
            )
            for problem in chosen_problems
        ]

        # Store the recommended problems in the database
        with transaction.atomic():
            RecommendedProblem.objects.bulk_create(recommended_problems_to_create)
        transaction.commit()

        logger.info(f'Problem recommendation completed for handle: {handle}')

    except Exception as e:
        logger.exception(f'Problem Recommendation Exception for handle: {handle}: {e}')

# =======================================================================
# =======================================================================

# @shared_task # commenting out as deploing background worker is paid
def update_problemset():
    # Get or create the update object for problemset
    update, _ = Update.objects.get_or_create(name='problemset_update')

    # Get the last update time
    update_time = update.epoch_time
    update_time = datetime.datetime.fromtimestamp(update_time)
    update_time = datetime.datetime(update_time.year, update_time.month, update_time.day)

    # Get the current time
    current_time = datetime.datetime.now()
    current_time = datetime.datetime(current_time.year, current_time.month, current_time.day)
    
    # Check if an update is required
    if update_time != current_time:
        logger.info(f'Updating Problemset | Today: {current_time}')
        
        try:
            # Fetch problemset data from Codeforces API
            data = GetJSON()
            data.fetch('https://codeforces.com/api/problemset.problems')
            problemset = data.json['result']['problems']
            
            # Get existing problem IDs and tags
            existing_problem_ids = set(Problem.objects.values_list("problem_id", flat=True))
            existing_tags = {tag.name: tag for tag in Tag.objects.all()}
            total_problem_processed = 0
            
            with transaction.atomic():
                problems_to_create = []
                problems_tags = {}
                
                for problem_data in problemset:
                    problem_id = str(problem_data.get('contestId')) + '.' + problem_data.get('index')
                    
                    # Check if the problem is not already in the database
                    if problem_id not in existing_problem_ids:
                        # Create a new problem object
                        problem = Problem(
                            problem_id=problem_id, 
                            name=problem_data.get('name'),
                            rating=problem_data.get('rating', 0)
                        )
                        problems_to_create.append(problem)
                        
                        # Build the list of tags for the problem
                        if problem_id not in problems_tags:
                            problems_tags[problem_id] = []
                            
                        for tag_name in problem_data['tags']:
                            if tag_name in existing_tags:
                                problems_tags[problem_id].append(existing_tags[tag_name])
                            else:    
                                problems_tags[problem_id].append(Tag.objects.get_or_create(name=tag_name)[0])
                        
                    # Batch create problems in the database
                    if len(problems_to_create) >= 100:
                        Problem.objects.bulk_create(problems_to_create)
                        
                        # Add tags to the created problems
                        for problem in problems_to_create:
                            for tag in problems_tags[problem.problem_id]:
                                problem.tags.add(tag)
                        
                        problems_to_create.clear()
                        problems_tags.clear()
                        logger.info("Batch created 100 problems")

                    total_problem_processed += 1
                    if total_problem_processed % 1000 == 0:
                        logger.info(f'Total {total_problem_processed} problems processed')

                # Create remaining problems in the database
                if problems_to_create:
                    Problem.objects.bulk_create(problems_to_create)
                    
                    # Add tags to the created problems
                    for problem in problems_to_create:
                        for tag in problems_tags[problem.problem_id]:
                            problem.tags.add(tag)
                    
                    logger.info(f"Batch created {len(problems_to_create)} problems")
                    
            transaction.commit()      
            
            # Update the last update time
            Update.objects.filter(name='problemset_update').update(epoch_time=int(current_time.timestamp()))
            
            logger.info("Problemset update completed successfully\n")
            
        except Exception as e:
            logger.exception(f'Problem set processing exception: {e}')
        
    else:
        logger.info(f'Problemset already updated | Last update: {update_time}\n')
