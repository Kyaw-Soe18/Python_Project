from multiprocessing.spawn import old_main_modules
from statistics import mode
from unicodedata import category
from django.db import models
from django.contrib.auth.models import User

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils import timezone


class Department(models.Model):
    name = models.CharField(max_length=250)
    description = models.TextField(blank=True, null=True)
    status = models.IntegerField(default = 1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    contact = models.CharField(max_length=250)
    dob = models.DateField(blank=True, null = True)
    address = models.TextField(blank=True, null = True)
    avatar = models.ImageField(blank=True, null = True, upload_to= 'images/')
    user_type = models.IntegerField(default = 2)
    gender = models.CharField(max_length=100, choices=[('Male','Male'),('Female','Female')], blank=True, null= True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, blank= True, null = True)

    def __str__(self):
        return self.user.username
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
   if created:
       UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    print(instance)
    try:
        profile = UserProfile.objects.get(user = instance)
    except Exception as e:
        UserProfile.objects.create(user=instance)
    instance.profile.save()

class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    name = models.CharField(max_length=250)
    status = models.IntegerField(default = 1)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Section(models.Model):
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, related_name='sections', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Student(models.Model):
    student_code = models.CharField(max_length=250,blank=True, null= True)
    course=models.ForeignKey(Course,on_delete=models.CASCADE)
    first_name = models.CharField(max_length=250)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, blank=True, null=True)  # ✅ Add this
    gender = models.CharField(max_length=100, choices=[('Male','Male'),('Female','Female')], blank=True, null= True)
    dob = models.DateField(blank=True, null= True)
    contact = models.CharField(max_length=250, blank=True, null= True)
    date_added = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        parts = [
            self.student_code or '',
            self.first_name or '',

        ]
        return ' - '.join(parts)

class Class(models.Model):
    assigned_faculty = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)  # 👈 Add this
    school_year = models.CharField(max_length=250)
    level = models.CharField(max_length=250)
    name = models.CharField(max_length=250)

    def __str__(self):
        return "[" + self.level + "] "+ self.level+ '-' +self.name

class ClassStudent(models.Model):
    classIns = models.ForeignKey(Class, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)

    def __str__(self):
        return self.student.student_code

    def get_present(self):
        student = self.student
        _class = self.classIns
        try:
            return Attendance.objects.filter(classIns=_class, student=student, type='1').count()
        except:
            return 0

    def get_absent(self):
        student = self.student
        _class = self.classIns
        try:
            return Attendance.objects.filter(classIns=_class, student=student, type='2').count()
        except:
            return 0


class Attendance(models.Model):
    classIns = models.ForeignKey(Class, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    attendance_date = models.DateField()
    type = models.CharField(
        max_length=250,
        choices=[
            ('1', 'Present'),
            ('2', 'Absent'),
        ]
    )
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.classIns.name}  {self.student.student_code}"
