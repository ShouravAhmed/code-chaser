from django.db import models

class Update(models.Model):
    name = models.CharField(max_length=50)
    epoch_time = models.IntegerField(default=0)

    def __str__(self) -> str:
        return self.name
    
class Problem(models.Model):
    problem_id = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    rating = models.IntegerField(default=0)
    tags = models.ManyToManyField('Tag')
    
    def __str__(self) -> str:
        return self.problem_id

class Tag(models.Model):
    name = models.CharField(max_length=50)
    
    def __str__(self) -> str:
        return self.name
    
class Submission(models.Model):
    handle = models.CharField(max_length=50, default="")
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True)
    submission_time = models.IntegerField(default=0)
    
    def __str__(self) -> str:
        return f'{self.problem.problem_id}.{self.handle}'

class RecommendedProblem(models.Model):
    handle = models.CharField(max_length=50)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, null=True, blank=True)
    date = models.IntegerField(default=0)
    
    def __str__(self) -> str:
        return f'{self.problem.problem_id}.{self.handle}'
